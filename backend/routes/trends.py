from flask import Blueprint, jsonify, request

from services.trends_service import get_trends

bp = Blueprint('trends', __name__)


@bp.route('/api/trends')
def trends():
    """`country` = ISO alpha-2 (e.g. IN), `wiki` = home wiki dbname, `langs` = extra
    language codes the editor reads (comma-separated)."""
    country = (request.args.get('country') or '').upper() or None
    dbname = request.args.get('wiki') or 'enwiki'
    langs = [l for l in (request.args.get('langs') or '').split(',') if l][:5]
    return jsonify(get_trends(country, dbname, langs))
