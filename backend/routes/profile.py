from flask import Blueprint, jsonify
from services.profile_service import fetch_contribs, fetch_categories, build_profile

bp = Blueprint("profile", __name__)


@bp.route("/api/profile/<username>", methods=["GET"])
def get_profile(username):
    try:
        contribs = fetch_contribs(username, limit=15000)
        articles = [c for c in contribs if (c.get("ns") or 0) == 0]
        unique_titles = list({c["title"] for c in articles})[:50]
        cat_map = fetch_categories(unique_titles)
        profile = build_profile(username, contribs, cat_map)
        return jsonify(profile)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Something went wrong: " + str(e)}), 500