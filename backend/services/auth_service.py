"""Optional login with a Wikimedia account (OAuth 2.0, authorization-code grant).

Compass works without it. Logging in adds what only the editor may read: their
watchlist (Revisit for every article they watch, not only ones they created or edited
a lot) and the topics and task types they picked on Special:Homepage (newcomer tasks
that match their own choice).

Register a consumer at https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration/propose/oauth2
("confidential client", grants: basic rights + "View your watchlist"; callback =
COMPASS_OAUTH_CALLBACK) and set COMPASS_OAUTH_CLIENT_ID / COMPASS_OAUTH_CLIENT_SECRET.
Without them, /api/auth/* reports `enabled: false` and the UI hides the login button.

Tokens are kept server-side in the store; the browser only gets an opaque, HttpOnly
session cookie.
"""
import json
import os
import secrets
import time
from urllib.parse import urlencode

from services import wiki, store

OAUTH_BASE = 'https://meta.wikimedia.org/w/rest.php/oauth2'
CLIENT_ID = os.environ.get('COMPASS_OAUTH_CLIENT_ID')
CLIENT_SECRET = os.environ.get('COMPASS_OAUTH_CLIENT_SECRET')
CALLBACK = os.environ.get('COMPASS_OAUTH_CALLBACK', 'http://127.0.0.1:5000/api/auth/callback')
SESSION_DAYS = 30
COOKIE = 'compass_session'

HOMEPAGE_TOPIC_PREFS = ('growthexperiments-homepage-se-topic-filters', 'growthexperiments-homepage-se-ores-topic-filters')
HOMEPAGE_TASK_PREF = 'growthexperiments-homepage-se-filters'


def enabled():
    return bool(CLIENT_ID and CLIENT_SECRET)


def authorize_url(state):
    return f'{OAUTH_BASE}/authorize?' + urlencode({
        'response_type': 'code', 'client_id': CLIENT_ID, 'state': state, 'redirect_uri': CALLBACK,
    })


def _token(grant):
    r = wiki.session.post(f'{OAUTH_BASE}/access_token', data={
        **grant, 'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'redirect_uri': CALLBACK,
    }, timeout=20)
    if not r.ok:
        raise wiki.UserError('Wikimedia login failed. Please try again.', 401)
    return r.json()


def _profile(access_token):
    r = wiki.session.get(f'{OAUTH_BASE}/resource/profile', headers={'Authorization': f'Bearer {access_token}'}, timeout=20)
    if not r.ok:
        raise wiki.UserError('Could not read your Wikimedia profile.', 401)
    return r.json()


def finish_login(code):
    """Exchanges the authorization code; returns (session id, username)."""
    tok = _token({'grant_type': 'authorization_code', 'code': code})
    username = _profile(tok['access_token'])['username']
    session_id = secrets.token_urlsafe(32)
    store.execute('INSERT INTO sessions (id, username, access_token, refresh_token, expires, created) VALUES (?, ?, ?, ?, ?, ?)',
                  (session_id, username, tok['access_token'], tok.get('refresh_token'),
                   time.time() + int(tok.get('expires_in') or 3600), time.time()))
    return session_id, username


def session_user(session_id):
    """{username, token} for a live session (refreshing the access token if it expired), or None."""
    if not session_id:
        return None
    s = store.row('SELECT * FROM sessions WHERE id = ?', (session_id,))
    if not s or s['created'] < time.time() - SESSION_DAYS * 86400:
        return None
    if s['expires'] <= time.time() + 60:
        if not s['refresh_token']:
            return None
        try:
            tok = _token({'grant_type': 'refresh_token', 'refresh_token': s['refresh_token']})
        except wiki.UserError:
            logout(session_id)
            return None
        store.execute('UPDATE sessions SET access_token = ?, refresh_token = ?, expires = ? WHERE id = ?',
                      (tok['access_token'], tok.get('refresh_token') or s['refresh_token'],
                       time.time() + int(tok.get('expires_in') or 3600), session_id))
        s['access_token'] = tok['access_token']
    return {'username': s['username'], 'token': s['access_token']}


def logout(session_id):
    store.execute('DELETE FROM sessions WHERE id = ?', (session_id,))


def watchlist(dbname, token, limit=500):
    """Article titles on the user's watchlist on one wiki."""
    data = wiki.api(dbname, {'action': 'query', 'list': 'watchlistraw', 'wrnamespace': 0, 'wrlimit': limit}, token=token)
    items = data.get('watchlistraw') or (data.get('query') or {}).get('watchlistraw') or []
    return [w['title'] for w in items]


def homepage_choices(dbname, token):
    """Topics and task types the user picked on Special:Homepage (empty if they never did)."""
    data = wiki.api(dbname, {'action': 'query', 'meta': 'userinfo', 'uiprop': 'options'}, token=token)
    options = ((data.get('query') or {}).get('userinfo') or {}).get('options') or {}

    def as_list(value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except ValueError:
            return [v for v in str(value).split('|') if v]
    topics = next((as_list(options.get(p)) for p in HOMEPAGE_TOPIC_PREFS if options.get(p)), [])
    return {'topics': topics, 'taskTypes': as_list(options.get(HOMEPAGE_TASK_PREF))}


def growth_tasks(dbname, token, topics=None, task_types=None, limit=30):
    """Growth's own suggested-edits list (`list=growthtasks`, logged-in users only), for
    the given topics. Returns [{title, tasktype, difficulty, ...}]."""
    params = {'action': 'query', 'list': 'growthtasks', 'gtlimit': limit}
    if topics:
        params['gttopics'] = '|'.join(topics)
        params['gttopicsmode'] = 'OR'
    if task_types:
        params['gttasktypes'] = '|'.join(task_types)
    data = wiki.api(dbname, params, token=token)
    # The module has put its result at the top level and under `query` in different versions.
    for node in (data.get('growthtasks'), (data.get('query') or {}).get('growthtasks')):
        if isinstance(node, dict) and isinstance(node.get('suggestions'), list):
            return node['suggestions']
        if isinstance(node, list):
            return node
    return []
