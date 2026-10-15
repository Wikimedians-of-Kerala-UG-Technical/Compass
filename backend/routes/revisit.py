from flask import Blueprint, jsonify, request

from services.profile_service import build_profile
from services.revisit_service import find_revisit

bp = Blueprint('revisit', __name__)


@bp.route('/api/revisit/<username>')
def get_revisit(username):
    profile = build_profile(username, request.args.get('wiki') or None)
    return jsonify({'username': profile['username'], **find_revisit(profile)})
