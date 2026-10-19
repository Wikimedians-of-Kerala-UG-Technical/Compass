from flask import Blueprint, jsonify, request

from services import feedback_service
from services.profile_service import build_profile
from services.task_service import find_tasks

bp = Blueprint('tasks', __name__)


@bp.route('/api/tasks/<username>')
def tasks(username):
    """Ranked tasks on the editor's home wiki. Optional `lat`, `lon` and `place` (from
    /api/geo's focus.local) add a "near where you edit" source."""
    profile = build_profile(username, request.args.get('wiki') or None)
    place = None
    lat, lon = request.args.get('lat', type=float), request.args.get('lon', type=float)
    if lat is not None and lon is not None:
        place = {'name': request.args.get('place') or 'your area', 'coord': {'lat': lat, 'lon': lon}}
    result = find_tasks(profile, place)
    # Tasks the editor voted down, dismissed or finished don't come back. They're returned
    # separately so the editor can restore one (undo).
    hidden = feedback_service.hidden_titles(profile['username'], profile['homeWiki'])
    if hidden:
        kept = [t for t in result['tasks'] if t['title'] not in hidden]
        removed = [t for t in result['tasks'] if t['title'] in hidden]
        result = {**result, 'tasks': kept, 'hidden': len(removed), 'hiddenTasks': removed}
    return jsonify(result)
