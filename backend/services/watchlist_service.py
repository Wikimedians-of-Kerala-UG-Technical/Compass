from services.profile_service import _wiki_get

# Maintenance-tag tracking categories (e.g. "Category:Articles lacking reliable
# references from March 2026") are HIDDEN categories, and their names don't literally
# contain words like "unreferenced" — match the substrings MediaWiki actually uses.
ISSUE_KEYWORDS = {
    'unsourced': 'now unreferenced',
    'additional references': 'now unreferenced',
    'reliable references': 'now unreferenced',
    'cleanup': 'flagged for cleanup',
    'disputed': 'accuracy disputed',
    'npov': 'neutrality disputed',
    'updat': 'needs update',  # matches both "updating" and "updated"
}


def find_watchlist_tasks(items):
    """
    items: [{title, count}] — articles the user has edited repeatedly. Flags ones that
    have since picked up maintenance-issue categories (unreferenced, cleanup, disputed,
    stale) since the user last worked on them.
    """
    if not items:
        return []
    count_map = {i['title']: i['count'] for i in items}
    titles = list(count_map.keys())

    tasks = []
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        try:
            data = _wiki_get({
                'action': 'query', 'titles': '|'.join(batch),
                'prop': 'categories', 'cllimit': 'max',
            })
        except Exception:
            continue
        pages = (data.get('query') or {}).get('pages') or {}
        for pg in pages.values():
            title = pg.get('title')
            if not title or (pg.get('ns') or 0) != 0:
                continue
            cats = [c['title'].lower() for c in pg.get('categories', [])]
            issues = sorted({label for kw, label in ISSUE_KEYWORDS.items() if any(kw in c for c in cats)})
            if issues:
                count = count_map.get(title, 0)
                tasks.append({
                    'title': title,
                    'type': 'watchlist',
                    'topic': 'personal',
                    'reason': f'You edited this {count}× — ' + ', '.join(issues),
                })
    return tasks


def find_followup_tasks(titles):
    """
    titles: articles the user created. Flags ones still in rough shape — still a stub,
    still unreferenced, or short enough to be worth expanding.
    """
    if not titles:
        return []

    tasks = []
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        try:
            data = _wiki_get({
                'action': 'query', 'titles': '|'.join(batch),
                'prop': 'info|categories', 'cllimit': 'max',
            })
        except Exception:
            continue
        pages = (data.get('query') or {}).get('pages') or {}
        for pg in pages.values():
            title = pg.get('title')
            if not title or (pg.get('ns') or 0) != 0:
                continue
            cats = [c['title'].lower() for c in pg.get('categories', [])]
            is_stub = any('stub' in c for c in cats)
            needs_ref = any(kw in c for c in cats for kw in ('unsourced', 'additional references', 'reliable references'))
            length = pg.get('length') or 99999
            is_short = length < 4000

            if not (is_stub or needs_ref or is_short):
                continue
            if is_stub:
                reason = 'You created this article — still a stub'
            elif needs_ref:
                reason = 'You created this article — needs references'
            else:
                reason = f'You created this article — could be expanded ({round(length / 1000)}k)'

            tasks.append({
                'title': title,
                'type': 'followup',
                'topic': 'personal',
                'isQuick': is_short and not is_stub,
                'reason': reason,
            })
    return tasks
