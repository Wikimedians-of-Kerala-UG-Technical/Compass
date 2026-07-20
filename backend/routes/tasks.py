from flask import Blueprint, jsonify, request

from services.trends_service import get_trends, wiki_get
from services.scoring_service import score_and_rank

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


@bp.route('/api/trends')
def trends():
    return jsonify(get_trends())


@bp.route('/api/tasks')
def tasks():
    topics = [t.strip() for t in request.args.get('topics', '').split(',') if t.strip()][:5]
    edit_types = [t.strip() for t in request.args.get('editTypes', '').split(',') if t.strip()]
    geo = request.args.get('geo', '').strip() or None

    # A geo focus needs 'geography' tasks to actually exist to apply its bonus to, even
    # if geography isn't one of the user's top edit topics.
    search_topics = topics or list(GENERIC_TOPICS)
    if geo and 'geography' not in search_topics:
        search_topics = search_topics + ['geography']

    raw_tasks = find_tasks_for_topics(search_topics)
    ranked = score_and_rank(raw_tasks, topics, edit_types, geo=geo)
    return jsonify(ranked)
