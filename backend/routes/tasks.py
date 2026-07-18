from flask import Blueprint, jsonify

from services.trends_service import get_trends, wiki_get

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


def find_generic_tasks():
    tasks = []
    seen = set()
    for topic in GENERIC_TOPICS:
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
    return jsonify(find_generic_tasks())
