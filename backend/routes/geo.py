from flask import Blueprint, jsonify, request

from services.profile_service import build_profile
from services.geo_service import resolve_geo

bp = Blueprint('geo', __name__)


@bp.route('/api/geo/<username>')
def get_geo(username):
    try:
        profile = build_profile(username, request.args.get('wiki') or None)
        geo = resolve_geo(profile['homeWiki'], profile['_editedTitles'])
        return jsonify({'username': username, 'wiki': profile['homeWiki'], **geo})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': 'Something went wrong: ' + str(e)}), 500
