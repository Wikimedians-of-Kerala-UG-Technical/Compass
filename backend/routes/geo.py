from flask import Blueprint, jsonify, request

from services.profile_service import build_profile
from services.geo_service import resolve_geo

bp = Blueprint('geo', __name__)


@bp.route('/api/geo/<username>')
def get_geo(username):
    try:
        profile = build_profile(username, request.args.get('wiki') or None)
        try:
            geo = resolve_geo(profile['homeWiki'], profile['_editedTitles'])
        except RuntimeError as e:  # Wikidata rate-limited or down: no focus, not a 500
            geo = {'articlesWithGeo': 0, 'topPlaces': [], 'topCountries': [],
                   'focus': {'region': None, 'local': None, 'country': None},
                   'partial': True, 'failed': [{'query': 'wikidata', 'error': str(e)}]}
        return jsonify({'username': username, 'wiki': profile['homeWiki'], **geo})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': 'Something went wrong: ' + str(e)}), 500
