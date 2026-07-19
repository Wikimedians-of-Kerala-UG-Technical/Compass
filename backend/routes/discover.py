import time

from flask import Blueprint, jsonify

from services.profile_service import fetch_contribs, fetch_categories, fetch_user_wikis
from services.category_service import (
    fetch_category_qids,
    fetch_article_qids,
    fetch_category_info,
    fetch_category_members,
    fetch_sitelinks,
    MEGA_CATEGORY_THRESHOLD,
    TOP_CATEGORIES,
    MEMBERS_PER_CATEGORY,
)

bp = Blueprint('discover', __name__)


@bp.route('/api/discover/<username>')
def get_discoveries(username):
    try:
        contribs = fetch_contribs(username, limit=1000)
        articles = [c for c in contribs if (c.get("ns") or 0) == 0]
        unique_titles = list({c["title"] for c in articles})
        unique_titles_set = set(unique_titles)

        cat_map = fetch_categories(unique_titles)

        unique_categories = sorted({cat for cats in cat_map.values() for cat in cats})
        qid_map = fetch_category_qids(unique_categories)

        category_counts = {}
        for cats in cat_map.values():
            for cat in cats:
                category_counts[cat] = category_counts.get(cat, 0) + 1

        categories = [
            {
                "name": name,
                "qid": qid,
                "wikidataUrl": f"https://www.wikidata.org/wiki/{qid}",
                "pageCount": category_counts.get(name, 0),
            }
            for name, qid in qid_map.items()
        ]
        categories.sort(key=lambda c: c["pageCount"], reverse=True)

        # -- New-article suggestions --
        # Expand the user's top categories into candidate articles they haven't
        # touched, skip mega-categories (their members aren't a real topical
        # signal), then flag candidates missing from the user's known languages.
        top_categories = categories[:TOP_CATEGORIES]
        info_map = fetch_category_info([c["name"] for c in top_categories])
        real_categories = [
            c for c in top_categories
            if info_map.get(c["name"], 0) <= MEGA_CATEGORY_THRESHOLD
        ]
        skipped_mega_categories = [c["name"] for c in top_categories if c not in real_categories]

        candidates = {}  # title -> {fromCategory, categoryWeight}
        for cat in real_categories:
            members = fetch_category_members(cat["name"], limit=MEMBERS_PER_CATEGORY)
            time.sleep(0.2)
            for title in members:
                if title in unique_titles_set:
                    continue
                existing = candidates.get(title)
                if not existing or cat["pageCount"] > existing["categoryWeight"]:
                    candidates[title] = {"fromCategory": cat["name"], "categoryWeight": cat["pageCount"]}

        candidate_qids = fetch_article_qids(list(candidates.keys()))
        user_wikis = fetch_user_wikis(username)

        suggested_articles = []
        if user_wikis and candidate_qids:
            sitelinks_map = fetch_sitelinks(set(candidate_qids.values()))
            for title, meta in candidates.items():
                qid = candidate_qids.get(title)
                if not qid:
                    continue
                present = sitelinks_map.get(qid, set())
                missing = [w for w in user_wikis if w["dbname"] not in present]
                if not missing:
                    continue
                suggested_articles.append({
                    "title": title,
                    "qid": qid,
                    "wikidataUrl": f"https://www.wikidata.org/wiki/{qid}",
                    "fromCategory": meta["fromCategory"],
                    "categoryWeight": meta["categoryWeight"],
                    "existsIn": sorted(present),
                    "missingIn": [{"dbname": w["dbname"], "url": w["url"]} for w in missing],
                })
        suggested_articles.sort(key=lambda a: a["categoryWeight"], reverse=True)

        return jsonify({
            "username": username,
            "editsFetched": len(contribs),
            "uniquePages": len(unique_titles),
            "uniqueCategories": len(unique_categories),
            "categoriesWithQid": len(categories),
            "categories": categories,
            "userWikis": user_wikis,
            "suggestedArticles": suggested_articles,
            "skippedMegaCategories": skipped_mega_categories,
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Something went wrong: " + str(e)}), 500
