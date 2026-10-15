from flask import Blueprint, jsonify, request

from services.profile_service import fetch_global_user, home_wiki
from services.stats_service import get_stats

bp = Blueprint('stats', __name__)


@bp.route('/api/stats/<username>')
def stats(username):
    """Streak, last-30-day activity and readers reached, on `wiki` (default: home wiki)."""
    dbname = request.args.get('wiki') or home_wiki(fetch_global_user(username))
    return jsonify(get_stats(username, dbname))
