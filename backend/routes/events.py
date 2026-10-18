from flask import Blueprint, jsonify, request

from services import event_service

bp = Blueprint('events', __name__, url_prefix='/api/events')


@bp.route('/resolve')
def resolve():
    """`?ref=` an event ID, a Special:EventDetails link or an Event: page -> {id}."""
    return jsonify({'id': event_service.resolve(request.args.get('ref'))})


@bp.route('/<int:event_id>')
def get(event_id):
    return jsonify(event_service.get_event(event_id))


@bp.route('/<int:event_id>/rank/<username>')
def rank(event_id, username):
    """The event's worklist ordered for this editor. Optional `wiki` picks which of the
    worklist's wikis to rank (default: the editor's home wiki, else the biggest)."""
    return jsonify(event_service.rank_for(event_id, username, request.args.get('wiki') or None))
