from flask import Blueprint, jsonify, request

from services.article_service import analyze_article
from services.references_service import find_external_references

bp = Blueprint('article', __name__, url_prefix='/api/article')


@bp.route('/<path:title>/guide', methods=['GET'])
def get_guide(title):
    """Paragraph-level analysis of one article on any wiki (`?wiki=mlwiki`, default enwiki)."""
    data = analyze_article(title, request.args.get('wiki') or 'enwiki')
    return jsonify(data), (404 if data.get('error') else 200)


@bp.route('/<path:title>/external-references', methods=['GET'])
def get_external_references(title):
    """Citable sources (PubMed/OpenAlex/CrossRef) with ready-to-paste citation templates."""
    return jsonify(find_external_references(title, request.args.get('wiki') or 'enwiki')), 200
