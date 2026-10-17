"""Live alerts from EventStreams: "your article was just edited / tagged".

One background thread reads Wikimedia's public recentchange stream (all wikis, ~50
events a second) while at least one browser is subscribed, and hands matching events
to each subscriber's queue:

- `edit`: someone else edited one of the editor's articles (created, heavily edited,
  or watched).
- `tagged` / `untagged`: one of those articles was added to or removed from a tracking
  category ("All articles lacking sources"). Categorize events say "[[:Title]] added to
  category" in the wiki's own language, so the article's current categories are
  re-read to tell which it was.
"""
import json
import logging
import queue
import re
import threading
import time
import uuid

from services import wiki, maintenance

STREAM_URL = 'https://stream.wikimedia.org/v2/stream/recentchange'
QUEUE_MAX = 100
log = logging.getLogger('compass.alerts')
LINK_RE = re.compile(r'^\[\[:?([^\]|]+)')


class AlertHub:
    def __init__(self, url=STREAM_URL):
        self.url = url
        self._subs = {}       # id -> subscription
        self._index = {}      # (wiki, title) -> set of subscription ids
        self._tracking = {}   # wiki -> {category name: issue key}
        self._lock = threading.Lock()
        self._thread = None
        self._last_id = None

    # -- subscriptions -------------------------------------------------------
    def subscribe(self, username, dbname, titles):
        sub_id = uuid.uuid4().hex
        sub = {'username': username, 'wiki': dbname, 'titles': set(titles), 'queue': queue.Queue(QUEUE_MAX)}
        tracking = self._tracking_categories(dbname)
        with self._lock:
            self._tracking[dbname] = tracking
            self._subs[sub_id] = sub
            for t in sub['titles']:
                self._index.setdefault((dbname, t), set()).add(sub_id)
            if not self._thread or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run, name='eventstreams', daemon=True)
                self._thread.start()
        return sub_id, sub['queue']

    def unsubscribe(self, sub_id):
        with self._lock:
            sub = self._subs.pop(sub_id, None)
            if not sub:
                return
            for t in sub['titles']:
                ids = self._index.get((sub['wiki'], t))
                if ids:
                    ids.discard(sub_id)
                    if not ids:
                        del self._index[(sub['wiki'], t)]

    def subscribers(self):
        with self._lock:
            return len(self._subs)

    @staticmethod
    def _tracking_categories(dbname):
        try:
            local = maintenance.local_issues(dbname)
        except RuntimeError:
            return {}
        return {v['category']: k for k, v in local.items() if v.get('category')}

    # -- the stream ----------------------------------------------------------
    def _run(self):
        backoff = 1
        while self.subscribers():
            try:
                headers = {'Accept': 'text/event-stream'}
                if self._last_id:
                    headers['Last-Event-ID'] = self._last_id
                with wiki.session.get(self.url, stream=True, timeout=(10, 60), headers=headers) as r:
                    r.raise_for_status()
                    backoff = 1
                    for line in r.iter_lines(chunk_size=4096, decode_unicode=True):
                        if not self.subscribers():
                            return
                        if line.startswith('id: '):
                            self._last_id = line[4:]
                        elif line.startswith('data: '):
                            try:
                                self.handle(json.loads(line[6:]))
                            except ValueError:
                                continue
            except Exception as e:  # dropped connection: reconnect from the last event id
                log.warning('EventStreams connection lost (%s); retrying in %ss', e, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)

    def handle(self, event):
        """Routes one recentchange event to matching subscribers."""
        dbname = event.get('wiki')
        kind = event.get('type')
        if kind in ('edit', 'new') and event.get('namespace') == 0:
            title = event.get('title')
            ids = self._match(dbname, title)
            if not ids:
                return
            rev = event.get('revision') or {}
            alert = {
                'kind': 'edit', 'title': title, 'wiki': dbname, 'user': event.get('user'),
                'comment': (event.get('comment') or '')[:200], 'bot': bool(event.get('bot')),
                'timestamp': event.get('timestamp'), 'url': wiki.page_url(dbname, title),
                'diffUrl': f'https://{wiki.host(dbname)}/w/index.php?diff={rev["new"]}' if rev.get('new') else None,
            }
            self._push(ids, alert, skip_user=event.get('user'))
        elif kind == 'categorize':
            category = (event.get('title') or '').split(':', 1)[-1]
            issue = self._tracking.get(dbname, {}).get(category)
            if not issue:
                return
            m = LINK_RE.match(event.get('comment') or '')
            title = m.group(1).strip() if m else None
            ids = self._match(dbname, title)
            if not ids:
                return
            present = self._has_category(dbname, title, category)
            alert = {
                'kind': 'tagged' if present else 'untagged', 'title': title, 'wiki': dbname,
                'issue': issue, 'label': maintenance.meta(issue)['short'], 'user': event.get('user'),
                'timestamp': event.get('timestamp'), 'url': wiki.page_url(dbname, title),
            }
            self._push(ids, alert)

    def _match(self, dbname, title):
        if not title:
            return set()
        with self._lock:
            return set(self._index.get((dbname, title), ()))

    def _push(self, ids, alert, skip_user=None):
        with self._lock:
            subs = [self._subs[i] for i in ids if i in self._subs]
        for sub in subs:
            if skip_user and skip_user == sub['username']:
                continue  # the editor's own edits aren't news to them
            try:
                sub['queue'].put_nowait(alert)
            except queue.Full:
                pass  # a stalled browser tab loses old alerts, not the stream

    @staticmethod
    def _has_category(dbname, title, category):
        try:
            pages = list(wiki.api_pages(dbname, [title], {
                'action': 'query', 'prop': 'categories', 'clcategories': f'Category:{category}',
            }))
        except RuntimeError:
            return True  # can't tell; a tracking-category event is usually a new tag
        return bool(pages and pages[0].get('categories'))


hub = AlertHub()
