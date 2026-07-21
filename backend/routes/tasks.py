from flask import Blueprint, jsonify, request

from services.trends_service import get_trends, wiki_get
from services.scoring_service import score_and_rank
from services.category_service import fetch_category_info, fetch_category_members

bp = Blueprint('tasks', __name__)

GENERIC_TOPICS = ['science', 'history', 'geography', 'biography', 'technology']

SEARCH_TEMPLATES = [
    ('Unreferenced', 'add_refs', 'Needs references'),
    ('Orphan', 'fix_orphan', 'Orphan article — add links from related pages'),
    ('Citation needed', 'add_citations', 'Has [citation needed] tags — add inline sources'),
]


def search_wiki(query, limit=4):
    try:
        d = wiki_get({
            'action': 'query', 'list': 'search', 'srsearch': query,
            'srlimit': limit, 'srnamespace': 0, 'srprop': 'snippet|size|wordcount'
        })
        return (d.get('query') or {}).get('search', [])
    except Exception:
        return []


def find_tasks_for_topics(topics):
    tasks = []
    seen = set()
    for topic in topics:
        for template, task_type, reason_prefix in SEARCH_TEMPLATES:
            results = search_wiki(f'hastemplate:"{template}" {topic}', 4)
            for r in results:
                title = r['title']
                if title in seen:
                    continue
                seen.add(title)
                tasks.append({
                    'title': title,
                    'type': task_type,
                    'topic': topic,
                    'reason': f'{reason_prefix} — {topic}',
                })
    return tasks


def find_regional_stub_tasks(geo):
    """
    Dynamic equivalent of the legacy hardcoded region -> Category:X_stubs map: try the
    resolved place name directly against Wikipedia's own "<Place> stubs" category
    naming convention, and just skip silently if that exact category doesn't exist
    (categoryinfo omits it, so `.get(..., 0)` is 0) -- works for whichever place name
    Wikipedia's stub-category convention actually covers, no hardcoded list needed.
    """
    if not geo:
        return []
    cat_name = f'{geo} stubs'
    info = fetch_category_info([cat_name])
    if not info.get(cat_name, 0):
        return []
    members = fetch_category_members(cat_name, limit=5)
    return [
        {
            'title': m,
            'type': 'expand_stub',
            'topic': geo,
            'reason': f'Stub in your geographic focus: {geo}',
        }
        for m in members
    ]


@bp.route('/api/trends')
def trends():
    return jsonify(get_trends())


@bp.route('/api/tasks')
def tasks():
    topics = [t.strip() for t in request.args.get('topics', '').split(',') if t.strip()][:5]
    edit_types = [t.strip() for t in request.args.get('editTypes', '').split(',') if t.strip()]
    geo = request.args.get('geo', '').strip() or None

    # The resolved place (e.g. "Kerala") is added as a genuine extra search topic, not
    # just a scoring nudge -- this is what actually surfaces region-specific results.
    search_topics = topics or list(GENERIC_TOPICS)
    if geo and geo not in search_topics:
        search_topics = search_topics + [geo]

    raw_tasks = find_tasks_for_topics(search_topics)
    raw_tasks += find_regional_stub_tasks(geo)
    ranked = score_and_rank(raw_tasks, topics, edit_types, geo=geo)
    return jsonify(ranked)
