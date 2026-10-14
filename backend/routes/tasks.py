from flask import Blueprint, jsonify, request

from services.profile_service import build_profile
from services.task_service import find_tasks

bp = Blueprint('tasks', __name__)


@bp.route('/api/tasks/<username>')
def tasks(username):
    """Ranked tasks on the editor's home wiki. Optional `lat`, `lon` and `place` (from
    /api/geo's focus.local) add a "near where you edit" source."""
    try:
        profile = build_profile(username, request.args.get('wiki') or None)
        place = None
        lat, lon = request.args.get('lat', type=float), request.args.get('lon', type=float)
        if lat is not None and lon is not None:
            place = {'name': request.args.get('place') or 'your area', 'coord': {'lat': lat, 'lon': lon}}
        return jsonify(find_tasks(profile, place))
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': 'Something went wrong: ' + str(e)}), 500
