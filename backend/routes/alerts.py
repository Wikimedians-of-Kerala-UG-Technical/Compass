import json
import queue

from flask import Blueprint, Response, request, stream_with_context

from services.alerts_service import hub
from services.profile_service import build_profile

bp = Blueprint('alerts', __name__)

KEEPALIVE_SECS = 25


@bp.route('/api/alerts/<username>/stream')
def stream(username):
    """Server-sent events for the editor's articles (created, heavily edited and the
    200 they edited most recently, plus the watchlist when logged in). Each event is a
    JSON alert from alerts_service; a comment line every 25 s keeps proxies from
    closing the connection. Needs a threaded server (gunicorn --threads). Only for the
    editor themselves: a live feed of someone else's articles would read as monitoring."""
    from routes.auth import current_user, require_owner
    require_owner(username)
    profile = build_profile(username, request.args.get('wiki') or None)
    titles = set(profile.get('createdArticles') or []) | {h['title'] for h in profile.get('heavilyEdited') or []}
    titles |= set(profile.get('_editedTitles') or [])
    user = current_user()
    if user:
        from services.auth_service import watchlist
        try:
            titles |= set(watchlist(profile['homeWiki'], user['token']))
        except RuntimeError:
            pass
    sub_id, q = hub.subscribe(profile['username'], profile['homeWiki'], titles)

    def events():
        try:
            yield f'event: ready\ndata: {json.dumps({"watching": len(titles), "wiki": profile["homeWiki"]})}\n\n'
            while True:
                try:
                    alert = q.get(timeout=KEEPALIVE_SECS)
                except queue.Empty:
                    yield ': keepalive\n\n'
                    continue
                yield f'event: alert\ndata: {json.dumps(alert, ensure_ascii=False)}\n\n'
        finally:
            hub.unsubscribe(sub_id)

    return Response(stream_with_context(events()), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
