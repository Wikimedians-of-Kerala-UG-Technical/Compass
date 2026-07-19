from flask import Blueprint, jsonify, request
from services.article_service import analyze_article, find_references, find_external_references

bp = Blueprint('article', __name__, url_prefix='/api/article')

@bp.route('/<title>/guide', methods=['GET'])
async def get_guide(title):
    """
    Returns the structural analysis and editing guide for a specific article.
    Matches the JSON contract expected by guide.js.
    """
    try:
        guide_data = await analyze_article(title)
        return jsonify(guide_data), 200
    except Exception as e:
        # Fallback to prevent crashing the whole request
        return jsonify({"error": str(e), "title": title, "suggestions": [], "missingExpected": []}), 500

@bp.route('/<title>/references', methods=['GET'])
async def get_references(title):
    """
    Returns a list of suggested references from Wikimedia APIs, paginated.
    Matches the JSON contract expected by guide.js.
    """
    try:
        offset = request.args.get('offset', default=0, type=int)
        references_data = await find_references(title, offset)
        return jsonify(references_data), 200
    except Exception as e:
        # Fallback to prevent crashing the whole request
        return jsonify({"error": str(e), "results": [], "nextOffset": None}), 500

@bp.route('/<title>/external-references', methods=['GET'])
async def get_external_references(title):
    """
    Returns a list of external academic references (Semantic Scholar, CrossRef, PubMed).
    """
    try:
        references_data = await find_external_references(title)
        return jsonify(references_data), 200
    except Exception as e:
        return jsonify({"error": str(e), "results": []}), 500
