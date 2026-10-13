"""Shared helpers for the Compass evaluation scripts. Read-only calls only."""
import os
import time

import requests

USER_AGENT = os.environ.get(
    'COMPASS_EVAL_UA',
    'CompassEval/1.0 (https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass; evaluation harness)',
)
BACKEND = os.environ.get('COMPASS_BACKEND', 'http://127.0.0.1:5000')

session = requests.Session()
session.headers['User-Agent'] = USER_AGENT


def api(wiki_host, **params):
    """GET a MediaWiki Action API (e.g. wiki_host='en.wikipedia.org'), retrying on 429."""
    params = {**params, 'format': 'json'}
    for attempt in range(4):
        r = session.get(f'https://{wiki_host}/w/api.php', params=params, timeout=60)
        if r.status_code == 429:
            time.sleep(int(r.headers.get('Retry-After', 2)) * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f'rate-limited by {wiki_host}')


def wiki_host(dbname):
    """'mlwiki' -> 'ml.wikipedia.org'. Only handles *wiki (Wikipedia) dbnames plus the big sister projects."""
    special = {
        'wikidatawiki': 'www.wikidata.org',
        'commonswiki': 'commons.wikimedia.org',
        'metawiki': 'meta.wikimedia.org',
    }
    if dbname in special:
        return special[dbname]
    if dbname.endswith('wiki'):
        return dbname[:-4].replace('_', '-') + '.wikipedia.org'
    raise ValueError(f'unsupported dbname {dbname}')


def safe_dirname(username):
    return username.replace('/', '_')
