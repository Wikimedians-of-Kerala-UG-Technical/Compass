from flask import Blueprint, jsonify, request
from services.article_service import analyze_article, find_references

bp = Blueprint('article', __name__, url_prefix='/api/article')

@bp.route('/<title>/guide', methods=['GET'])
def get_guide(title):
    """
    Returns the structural analysis and editing guide for a specific article.
    Matches the JSON contract expected by guide.js.
    """
    try:
        guide_data = analyze_article(title)
        return jsonify(guide_data), 200
    except Exception as e:
        # Fallback to prevent crashing the whole request
        return jsonify({"error": str(e), "title": title, "suggestions": [], "missingExpected": []}), 500

@bp.route('/<title>/references', methods=['GET'])
def get_references(title):
    """
    Returns a list of suggested references from Wikimedia APIs, paginated.
    Matches the JSON contract expected by guide.js.
    """
    try:
        offset = request.args.get('offset', default=0, type=int)
        references_data = find_references(title, offset)
        return jsonify(references_data), 200
    except Exception as e:
        # Fallback to prevent crashing the whole request
        return jsonify({"error": str(e), "results": [], "nextOffset": None}), 500
