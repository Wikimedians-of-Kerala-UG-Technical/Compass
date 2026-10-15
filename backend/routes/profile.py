from flask import Blueprint, jsonify, request

from services.profile_service import build_profile, public_profile

bp = Blueprint('profile', __name__)


@bp.route('/api/profile/<username>', methods=['GET'])
def get_profile(username):
    profile = build_profile(username, request.args.get('wiki') or None)
    return jsonify(public_profile(profile))
