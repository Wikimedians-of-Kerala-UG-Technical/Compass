from flask import Blueprint, jsonify, request

from services.profile_service import build_profile
from services.discover_service import find_discover

bp = Blueprint('discover', __name__)


@bp.route('/api/discover/<username>')
def get_discoveries(username):
    """Optional `region` and `local` (Wikidata QIDs) and `regionName`, from /api/geo's
    focus, add "missing in your language" gaps for those places."""
    profile = build_profile(username, request.args.get('wiki') or None)
    region = None
    if request.args.get('region') or request.args.get('local'):
        region = {'qid': request.args.get('region'), 'localQid': request.args.get('local'),
                  'name': request.args.get('regionName')}
    return jsonify({'username': profile['username'], **find_discover(profile, region)})
