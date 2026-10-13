"""One HTTP client for every Wikimedia API Compass calls.

Every request goes through here so the User-Agent, retry/backoff, `maxlag` and
POST batching are handled in one place, for any wiki (`dbname`), not just enwiki.
"""
import os
import re
import threading
import time

import requests

USER_AGENT = os.environ.get(
    'COMPASS_USER_AGENT',
    'Compass/2.0 (https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass) python-requests',
)
TIMEOUT = 30

session = requests.Session()
session.headers.update({'User-Agent': USER_AGENT, 'Accept': 'application/json'})
adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=40)
session.mount('https://', adapter)

SPECIAL_HOSTS = {
    'wikidatawiki': 'www.wikidata.org',
    'commonswiki': 'commons.wikimedia.org',
    'metawiki': 'meta.wikimedia.org',
}
# Wikis that show up in globaluserinfo but aren't real content Wikipedias.
NON_CONTENT_WIKIS = {'testwiki', 'test2wiki', 'abstractwiki', 'simplewiki_test'}


def host(dbname):
    """'mlwiki' -> 'ml.wikipedia.org'; 'wikidatawiki' -> 'www.wikidata.org'."""
    if dbname in SPECIAL_HOSTS:
        return SPECIAL_HOSTS[dbname]
    if dbname.endswith('wiki'):
        return dbname[:-4].replace('_', '-') + '.wikipedia.org'
    raise ValueError(f'Unsupported wiki: {dbname}')


def lang(dbname):
    """'mlwiki' -> 'ml', 'zh_min_nanwiki' -> 'zh-min-nan'."""
    return dbname[:-4].replace('_', '-') if dbname.endswith('wiki') else dbname


def dbname_from_url(url):
    """'https://ml.wikipedia.org' -> 'mlwiki' (Wikipedias only)."""
    m = re.match(r'^https://([a-z0-9-]+)\.wikipedia\.org$', url or '')
    return m.group(1).replace('-', '_') + 'wiki' if m else None


def is_content_wikipedia(dbname):
    return bool(dbname) and dbname.endswith('wiki') and dbname not in SPECIAL_HOSTS \
        and dbname not in NON_CONTENT_WIKIS and not dbname.startswith('test')


def page_url(dbname, title):
    return f'https://{host(dbname)}/wiki/{quote_title(title)}'


def edit_url(dbname, title):
    return f'https://{host(dbname)}/w/index.php?title={quote_title(title)}&action=edit'


def quote_title(title):
    from urllib.parse import quote
    return quote((title or '').replace(' ', '_'), safe='/:()\',')


def _request(method, url, retries=4, **kwargs):
    kwargs.setdefault('timeout', TIMEOUT)
    last = None
    for attempt in range(retries):
        try:
            r = session.request(method, url, **kwargs)
        except requests.RequestException as e:
            last = e
            time.sleep(1 + attempt)
            continue
        if r.status_code in (429, 502, 503, 504):
            wait = int(r.headers.get('Retry-After', 2) or 2)
            time.sleep(min(wait * (attempt + 1), 15))
            last = RuntimeError(f'{r.status_code} from {url}')
            continue
        return r
    raise RuntimeError(f'Request to {url} failed after {retries} attempts: {last}')


def api(dbname, params, post=False):
    """MediaWiki Action API call on any wiki. Uses POST for batches (long titles lists
    in non-Latin scripts overflow GET URLs). Raises on API errors. Compass only reads
    and serves a waiting user, so it doesn't send `maxlag` (that's for bots), but it
    still backs off if the API reports lag."""
    params = {**params, 'format': 'json', 'formatversion': 2}
    url = f'https://{host(dbname)}/w/api.php'
    for _ in range(3):
        r = _request('POST', url, data=params) if post else _request('GET', url, params=params)
        r.raise_for_status()
        data = r.json()
        err = data.get('error')
        if err and err.get('code') == 'maxlag':
            time.sleep(int(r.headers.get('Retry-After', 5)))
            continue
        if err:
            raise RuntimeError(f"{dbname} API error {err.get('code')}: {err.get('info')}")
        return data
    raise RuntimeError(f'{dbname} is lagged; try again shortly')


def api_pages(dbname, titles, params, batch=50):
    """Runs `params` over `titles` in batches of 50 (POST) and yields each page dict."""
    titles = [t for t in titles if t]
    for i in range(0, len(titles), batch):
        data = api(dbname, {**params, 'titles': '|'.join(titles[i:i + batch])}, post=True)
        yield from (data.get('query') or {}).get('pages') or []


def search(dbname, query, limit=10, sort=None, offset=0):
    """CirrusSearch. Returns (results, totalhits)."""
    params = {
        'action': 'query', 'list': 'search', 'srsearch': query, 'srlimit': limit,
        'srnamespace': 0, 'srprop': 'size|wordcount|timestamp', 'sroffset': offset,
    }
    if sort:
        params['srsort'] = sort
    data = api(dbname, params)
    q = data.get('query') or {}
    return q.get('search', []), (q.get('searchinfo') or {}).get('totalhits', 0)


def get_json(url, params=None, retries=3, timeout=TIMEOUT):
    """GET a JSON service. Returns None on any failure (callers treat it as missing)."""
    try:
        r = _request('GET', url, params=params, retries=retries, timeout=timeout)
    except RuntimeError:
        return None
    if not r.ok:
        return None
    try:
        return r.json()
    except ValueError:
        return None


def post_json(url, body, retries=3, timeout=TIMEOUT):
    """POST JSON to a service. Returns None on any failure."""
    try:
        r = _request('POST', url, json=body, retries=retries, timeout=timeout)
    except RuntimeError:
        return None
    if not r.ok:
        return None
    try:
        return r.json()
    except ValueError:
        return None


def get_text(url, timeout=TIMEOUT):
    r = _request('GET', url, timeout=timeout, headers={'Accept': 'text/html'})
    r.raise_for_status()
    return r.text


class TTLCache:
    """Tiny thread-safe in-memory cache. Keys expire after `ttl` seconds."""

    def __init__(self, ttl, maxsize=2000):
        self.ttl, self.maxsize = ttl, maxsize
        self._data = {}
        self._lock = threading.Lock()
        self._key_locks = {}

    def get(self, key):
        with self._lock:
            hit = self._data.get(key)
            if hit and hit[0] > time.time():
                return hit[1]
            return None

    def set(self, key, value):
        with self._lock:
            if len(self._data) >= self.maxsize:
                oldest = min(self._data, key=lambda k: self._data[k][0])
                self._data.pop(oldest, None)
            self._data[key] = (time.time() + self.ttl, value)
        return value

    def get_or_compute(self, key, fn):
        """Computes once per key even when several requests ask at the same time
        (the dashboard fires profile/tasks/geo/revisit in parallel)."""
        value = self.get(key)
        if value is not None:
            return value
        with self._lock:
            key_lock = self._key_locks.setdefault(key, threading.Lock())
        with key_lock:
            value = self.get(key)
            if value is None:
                value = self.set(key, fn())
        return value
