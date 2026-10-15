from flask import Blueprint, jsonify, request

from services.profile_service import build_profile
from services.crossproject_service import find_contribute

bp = Blueprint('contribute', __name__)


@bp.route('/api/contribute/<username>')
def get_contribute(username):
    """Commons and Wikidata tasks. Optional `place` (Wikidata QID) and `placeName`,
    from /api/geo's focus, scope the Wikidata gaps."""
    profile = build_profile(username, request.args.get('wiki') or None)
    place = None
    if request.args.get('place'):
        place = {'qid': request.args['place'], 'name': request.args.get('placeName')}
    return jsonify({'username': profile['username'], **find_contribute(profile, place)})
