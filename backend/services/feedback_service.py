"""Task feedback: what editors thought of a suggestion, and whether they then edited it.

Each card in Tasks can be voted up or down, marked done, or dismissed. The ranking
signals the task was shown with are stored next to the vote, so the hand-set weights in
task_service can later be fitted to real outcomes (`eval/learn_weights.py`). A vote
needs no login, so an "edited" outcome is only counted once the editor's own edit on
that article shows up in their contributions.
"""
import time
from datetime import datetime, timezone

from services import wiki, store

ACTIONS = ('up', 'down', 'done', 'dismiss')
HIDDEN = ('down', 'done', 'dismiss')  # no longer shown in that editor's task list
SIGNAL_KEYS = ('topic', 'place', 'impact', 'feasibility', 'freshness', 'affinity')
VERIFY_WINDOW_DAYS = 60


def record(username, dbname, title, action, task_type=None, scope=None, signals=None, score=None):
    username = wiki.normalize_username(username)
    title = (title or '').strip()
    if action not in ACTIONS:
        raise wiki.UserError(f'Unknown feedback action "{action}".', 400)
    if not username or not title or len(title) > 255:
        raise wiki.UserError('Feedback needs a username and an article title.', 400)
    wiki.host(dbname)  # raises UserError for an unknown wiki
    clean = {k: float(v) for k, v in (signals or {}).items() if k in SIGNAL_KEYS and isinstance(v, (int, float))}
    cur = store.execute(
        'INSERT INTO feedback (username, wiki, title, task_type, action, scope, signals, score, created) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (username, dbname, title, (task_type or '')[:40] or None, action, (scope or '')[:300] or None,
         store.dumps(clean or None), float(score) if isinstance(score, (int, float)) else None, time.time()))
    return {'id': cur.lastrowid, 'username': username, 'wiki': dbname, 'title': title, 'action': action}


def latest(username, dbname):
    """{title: latest feedback row} for this editor on this wiki."""
    out = {}
    for r in store.rows('SELECT * FROM feedback WHERE username = ? AND wiki = ? ORDER BY created',
                        (wiki.normalize_username(username), dbname)):
        out[r['title']] = r
    return out


def hidden_titles(username, dbname):
    return {t for t, r in latest(username, dbname).items() if r['action'] in HIDDEN}


def verify_edits(username, dbname):
    """Marks feedback rows whose article the editor has edited since. Returns how many
    rows were newly marked. One contributions call covers every pending row."""
    username = wiki.normalize_username(username)
    since = time.time() - VERIFY_WINDOW_DAYS * 86400
    pending = store.rows('SELECT id, title, created FROM feedback WHERE username = ? AND wiki = ? '
                         'AND edited_at IS NULL AND created >= ?', (username, dbname, since))
    if not pending:
        return 0
    oldest = min(p['created'] for p in pending)
    data = wiki.api(dbname, {
        'action': 'query', 'list': 'usercontribs', 'ucuser': username, 'uclimit': 500,
        'ucprop': 'title|timestamp', 'ucnamespace': 0,
        'ucend': datetime.fromtimestamp(oldest, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    })
    edits = {}
    for c in (data.get('query') or {}).get('usercontribs') or []:
        edits.setdefault(c['title'], []).append(c['timestamp'])
    marked = 0
    for p in pending:
        shown_at = datetime.fromtimestamp(p['created'], timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        after = sorted(t for t in edits.get(p['title'], []) if t >= shown_at)
        if after:
            store.execute('UPDATE feedback SET edited_at = ? WHERE id = ?', (after[0], p['id']))
            marked += 1
    return marked


def summary(username, dbname):
    """Counts for the editor's stats page."""
    username = wiki.normalize_username(username)
    rows = store.rows('SELECT action, edited_at FROM feedback WHERE username = ? AND wiki = ?', (username, dbname))
    counts = {a: 0 for a in ACTIONS}
    for r in rows:
        counts[r['action']] += 1
    return {**counts, 'edited': sum(1 for r in rows if r['edited_at'])}


def training_rows():
    """(signals, label) pairs for fitting ranking weights: 1 for up/done/edited,
    0 for down/dismiss. Rows without signals are skipped."""
    out = []
    for r in store.rows('SELECT action, signals, edited_at FROM feedback WHERE signals IS NOT NULL'):
        sig = store.loads(r['signals'])
        if not sig:
            continue
        label = 1 if (r['edited_at'] or r['action'] in ('up', 'done')) else 0
        out.append(({k: sig.get(k, 0.0) for k in SIGNAL_KEYS}, label))
    return out
