from flask import Blueprint, jsonify, request

from routes.auth import is_owner
from services import wiki
from services.profile_service import check_opt_out, fetch_global_user, home_wiki
from services.stats_service import get_stats

bp = Blueprint('stats', __name__)


@bp.route('/api/stats/<username>')
def stats(username):
    """Streak, last-30-day activity and readers reached, on `wiki` (default: home wiki)."""
    check_opt_out(wiki.normalize_username(username))
    dbname = request.args.get('wiki') or home_wiki(fetch_global_user(username))
    result = get_stats(username, dbname)
    if not is_owner(username):
        result = {**result, 'compass': None}  # their votes are private
    return jsonify(result)
