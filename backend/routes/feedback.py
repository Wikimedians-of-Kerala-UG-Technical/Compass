from flask import Blueprint, jsonify, request

from routes.auth import require_owner
from services import feedback_service

bp = Blueprint('feedback', __name__)


@bp.route('/api/feedback', methods=['POST'])
def post_feedback():
    """Body: {username, wiki, title, action: up|down|done|dismiss, type?, scope?, signals?, score?}."""
    body = request.get_json(silent=True) or {}
    require_owner(body.get('username') or '')
    saved = feedback_service.record(
        body.get('username'), body.get('wiki') or 'enwiki', body.get('title'), body.get('action'),
        task_type=body.get('type'), scope=body.get('scope'), signals=body.get('signals'), score=body.get('score'))
    return jsonify(saved), 201


@bp.route('/api/feedback/<username>', methods=['DELETE'])
def clear_feedback(username):
    """Undo: `?wiki=&title=` removes the editor's vote on that article."""
    require_owner(username)
    dbname = request.args.get('wiki') or 'enwiki'
    title = request.args.get('title')
    return jsonify({'title': title, 'cleared': feedback_service.clear(username, dbname, title)})


@bp.route('/api/feedback/<username>')
def get_feedback(username):
    """The editor's latest feedback per article, after checking which ones they've edited.
    Votes are private to the editor."""
    require_owner(username)
    dbname = request.args.get('wiki') or 'enwiki'
    try:
        feedback_service.verify_edits(username, dbname)
    except RuntimeError:
        pass  # contributions unavailable right now; votes are still returned
    items = [{'title': r['title'], 'action': r['action'], 'type': r['task_type'], 'editedAt': r['edited_at']}
             for r in feedback_service.latest(username, dbname).values()]
    return jsonify({'wiki': dbname, 'items': items, 'summary': feedback_service.summary(username, dbname)})
