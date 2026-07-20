import json

from flask import Blueprint, jsonify, request

from services.watchlist_service import find_watchlist_tasks, find_followup_tasks

bp = Blueprint('revisit', __name__)


def _parse_json_arg(name, max_items):
    raw = request.args.get(name, '')
    if not raw:
        return []
    try:
        items = json.loads(raw)
        return items[:max_items] if isinstance(items, list) else []
    except (ValueError, TypeError):
        return []


@bp.route('/api/revisit/<username>')
def get_revisit(username):
    # watch: [{title, count}] — the user's heavily-edited articles (profile.heavilyEdited)
    # mine: [title, ...] — articles the user created (profile.createdArticles)
    watch_items = [
        i for i in _parse_json_arg('watch', 15)
        if isinstance(i, dict) and i.get('title') and isinstance(i.get('count'), int)
    ]
    mine_titles = [t for t in _parse_json_arg('mine', 20) if isinstance(t, str)]

    by_title = {}
    for task in find_watchlist_tasks(watch_items) + find_followup_tasks(mine_titles):
        existing = by_title.get(task['title'])
        if not existing:
            by_title[task['title']] = task
            continue
        # Same article surfaced from both sources (heavily-edited AND self-created) — merge tags.
        existing_keys = {t['key'] for t in existing['tags']}
        for tag in task['tags']:
            if tag['key'] not in existing_keys:
                existing['tags'].append(tag)
                existing_keys.add(tag['key'])

    tasks = sorted(by_title.values(), key=lambda t: len(t['tags']), reverse=True)
    return jsonify({'username': username, 'tasks': tasks})
