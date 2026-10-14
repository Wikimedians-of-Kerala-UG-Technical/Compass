"""One HTTP client for every Wikimedia API Compass calls.

Every request goes through here so the User-Agent, retry/backoff, `maxlag` and
POST batching are handled in one place, for any wiki (`dbname`), not just enwiki.
"""
import os
import pickle
import re
import sqlite3
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


# At most this many requests in flight per host, across all users. Without it, a few
# dashboards loading at once sent ~20 parallel requests to Wikidata and got 429s.
HOST_CONCURRENCY = {'www.wikidata.org': 4}
_host_slots = {h: threading.BoundedSemaphore(n) for h, n in HOST_CONCURRENCY.items()}


def _request(method, url, retries=4, **kwargs):
    kwargs.setdefault('timeout', TIMEOUT)
    slot = _host_slots.get(url.split('/')[2])
    last = None
    for attempt in range(retries):
        try:
            if slot:
                with slot:
                    r = session.request(method, url, **kwargs)
            else:
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


# Caches are also written to SQLite, so a restart (or another worker) doesn't start
# cold. The slow parts of a cold dashboard are the same for everyone (a state's
# Wikidata item, a wiki's local template names), so a warm disk cache helps new
# editors too. Set COMPASS_CACHE_PATH to an empty string to keep caches in memory only.
CACHE_PATH = os.environ.get('COMPASS_CACHE_PATH', os.path.join(os.path.dirname(__file__), '..', '.cache', 'compass.sqlite3'))
_db_local = threading.local()


def _db():
    conn = getattr(_db_local, 'conn', None)
    if conn is None:
        os.makedirs(os.path.dirname(os.path.abspath(CACHE_PATH)), exist_ok=True)
        conn = sqlite3.connect(CACHE_PATH, timeout=10)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('CREATE TABLE IF NOT EXISTS cache (ns TEXT, key TEXT, expires REAL, value BLOB, PRIMARY KEY (ns, key))')
        _db_local.conn = conn
    return conn


class TTLCache:
    """Thread-safe cache. Keys expire after `ttl` seconds. With a `name`, entries are
    also kept on disk (see CACHE_PATH); the in-memory copy is checked first."""

    def __init__(self, ttl, maxsize=2000, name=None):
        self.ttl, self.maxsize = ttl, maxsize
        self.name = name if CACHE_PATH else None
        self._data = {}
        self._lock = threading.Lock()
        self._key_locks = {}

    def _disk_get(self, key):
        try:
            row = _db().execute('SELECT expires, value FROM cache WHERE ns = ? AND key = ?',
                                (self.name, repr(key))).fetchone()
        except sqlite3.Error:
            return None
        if not row or row[0] <= time.time():
            return None
        try:
            return row[0], pickle.loads(row[1])
        except Exception:
            return None

    def _disk_set(self, key, expires, value):
        try:
            conn = _db()
            conn.execute('INSERT OR REPLACE INTO cache VALUES (?, ?, ?, ?)',
                         (self.name, repr(key), expires, pickle.dumps(value, pickle.HIGHEST_PROTOCOL)))
            conn.commit()
        except (sqlite3.Error, pickle.PicklingError, TypeError):
            pass

    def get(self, key):
        with self._lock:
            hit = self._data.get(key)
            if hit and hit[0] > time.time():
                return hit[1]
        if not self.name:
            return None
        hit = self._disk_get(key)
        if hit is None:
            return None
        self._remember(key, *hit)
        return hit[1]

    def _remember(self, key, expires, value):
        with self._lock:
            if len(self._data) >= self.maxsize:
                oldest = min(self._data, key=lambda k: self._data[k][0])
                self._data.pop(oldest, None)
            self._data[key] = (expires, value)

    def set(self, key, value):
        expires = time.time() + self.ttl
        self._remember(key, expires, value)
        if self.name:
            self._disk_set(key, expires, value)
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


def purge_expired_cache():
    """Drops expired rows from the disk cache. Called once at startup."""
    if not CACHE_PATH:
        return
    try:
        conn = _db()
        conn.execute('DELETE FROM cache WHERE expires <= ?', (time.time(),))
        conn.commit()
    except sqlite3.Error:
        pass
