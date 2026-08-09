from flask import Blueprint, jsonify

from services.profile_service import fetch_contribs
from services.category_service import fetch_article_qids
from services.geo_service import resolve_geo_chains

bp = Blueprint('geo', __name__)


@bp.route('/api/geo/<username>')
def get_geo(username):
    try:
        contribs = fetch_contribs(username, limit=1000)
        articles = [c for c in contribs if (c.get("ns") or 0) == 0]
        unique_titles = list({c["title"] for c in articles})

        qid_map = fetch_article_qids(unique_titles)  # title -> qid
        chains = resolve_geo_chains(set(qid_map.values()))  # qid -> [place, ..., country]

        # Every level in every chain counts -- a "Kochi" edit and a "Kerala" edit are
        # both real signal, not just the country they both roll up to.
        place_counts = {}
        country_counts = {}
        for chain in chains.values():
            for name in chain:
                place_counts[name] = place_counts.get(name, 0) + 1
            country_counts[chain[-1]] = country_counts.get(chain[-1], 0) + 1

        top_places = sorted(place_counts.items(), key=lambda kv: kv[1], reverse=True)[:12]
        top_countries = sorted(country_counts.items(), key=lambda kv: kv[1], reverse=True)[:3]

        return jsonify({
            "username": username,
            "articlesWithGeo": len(chains),
            "topPlaces": [{"name": n, "count": c} for n, c in top_places],
            "topCountries": [{"name": n, "count": c} for n, c in top_countries],
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Something went wrong: " + str(e)}), 500
