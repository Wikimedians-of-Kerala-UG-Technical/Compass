import os
import secrets

from flask import Blueprint, jsonify, redirect, request, session

from services import auth_service, wiki
from services.profile_service import build_profile
from services.revisit_service import find_revisit

bp = Blueprint('auth', __name__)

WATCHLIST_MAX = 300


def _allowed_return(url):
    """Only redirect back to the frontend, never to an arbitrary site."""
    allowed = [o for o in (os.environ.get('COMPASS_FRONTEND_URL', ''),
                           *os.environ.get('COMPASS_CORS_ORIGINS', '').split(','),
                           'http://localhost:5173', 'http://127.0.0.1:5173') if o and o != '*']
    return any(url == o or url.startswith(o.rstrip('/') + '/') for o in allowed)


def current_user():
    return auth_service.session_user(request.cookies.get(auth_service.COOKIE))


def is_owner(username):
    """Logged in as this editor. Votes, alerts and private data are only for the owner of a
    dashboard; anyone else sees the public view (public edit history only)."""
    user = current_user()
    return bool(user) and user['username'] == wiki.normalize_username(username)


def require_owner(username):
    if not is_owner(username):
        name = wiki.normalize_username(username)
        raise wiki.UserError(f'Only {name}, logged in with their Wikimedia account, can do this.', 403)


def _require_user():
    user = current_user()
    if not user:
        raise wiki.UserError('Log in with your Wikimedia account first.', 401)
    return user


@bp.route('/api/auth/status')
def status():
    user = current_user() if auth_service.enabled() else None
    return jsonify({'enabled': auth_service.enabled(), 'username': user['username'] if user else None})


@bp.route('/api/auth/login')
def login():
    if not auth_service.enabled():
        raise wiki.UserError('Login is not configured on this server.', 404)
    back = request.args.get('return') or os.environ.get('COMPASS_FRONTEND_URL') or 'http://127.0.0.1:5173/'
    if not _allowed_return(back):
        raise wiki.UserError('That return address is not allowed.', 400)
    session['oauth_state'] = state = secrets.token_urlsafe(24)
    session['oauth_return'] = back
    return redirect(auth_service.authorize_url(state))


@bp.route('/api/auth/callback')
def callback():
    state = session.pop('oauth_state', None)
    back = session.pop('oauth_return', None) or os.environ.get('COMPASS_FRONTEND_URL') or '/'
    if not state or not secrets.compare_digest(state, request.args.get('state') or ''):
        raise wiki.UserError('Login expired or was started elsewhere. Please try again.', 400)
    if not request.args.get('code'):
        return redirect(back)  # the user declined on Meta
    session_id, _ = auth_service.finish_login(request.args['code'])
    resp = redirect(back)
    resp.set_cookie(auth_service.COOKIE, session_id, max_age=auth_service.SESSION_DAYS * 86400,
                    httponly=True, samesite='Lax', secure=request.is_secure)
    return resp


@bp.route('/api/auth/logout', methods=['POST'])
def logout():
    sid = request.cookies.get(auth_service.COOKIE)
    if sid:
        auth_service.logout(sid)
    resp = jsonify({'ok': True})
    resp.delete_cookie(auth_service.COOKIE)
    return resp


@bp.route('/api/me/revisit')
def my_revisit():
    """Revisit including every article on the logged-in editor's watchlist."""
    user = _require_user()
    profile = build_profile(user['username'], request.args.get('wiki') or None)
    watched = auth_service.watchlist(profile['homeWiki'], user['token'])[:WATCHLIST_MAX]
    return jsonify({'username': profile['username'], 'watchlist': len(watched), **find_revisit(profile, watched)})


@bp.route('/api/me/newcomer-tasks')
def my_newcomer_tasks():
    """Growth's suggested edits for the topics the editor chose on Special:Homepage."""
    user = _require_user()
    dbname = request.args.get('wiki') or build_profile(user['username'])['homeWiki']
    choices = auth_service.homepage_choices(dbname, user['token'])
    suggestions = auth_service.growth_tasks(dbname, user['token'], choices['topics'], choices['taskTypes'])
    tasks = [{
        'title': s.get('title'), 'wiki': dbname, 'type': s.get('tasktype'), 'difficulty': s.get('difficulty'),
        'url': wiki.page_url(dbname, s.get('title')),
        'editUrl': wiki.edit_url(dbname, s.get('title')),
    } for s in suggestions if s.get('title')]
    return jsonify({'wiki': dbname, 'homepage': choices, 'tasks': tasks})
