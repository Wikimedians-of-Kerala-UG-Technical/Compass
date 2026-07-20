from services.profile_service import _wiki_get

# Maintenance-tag tracking categories (e.g. "Category:Articles lacking reliable
# references from March 2026") are HIDDEN categories, and their names don't literally
# contain words like "unreferenced" — match the substrings MediaWiki actually uses.
# Each keyword maps to a (tag_key, tag_label) pair so callers can filter/group by tag.
ISSUE_TAGS = {
    'unsourced statements': ('add_citations', 'Citation needed'),
    'additional references': ('add_refs', 'Unreferenced'),
    'reliable references': ('add_refs', 'Unreferenced'),
    'lacking sources': ('add_refs', 'Unreferenced'),
    'orphaned articles': ('fix_orphan', 'Orphan'),
    'cleanup': ('cleanup', 'Cleanup'),
    'disputed': ('disputed', 'Accuracy disputed'),
    'npov': ('npov', 'Neutrality disputed'),
    'updat': ('stale', 'Needs update'),  # matches both "updating" and "updated"
}


def _tags_from_categories(cats):
    """cats: lowercased category titles. Returns deduped [{key, label}] issue tags."""
    seen = {}
    for kw, (key, label) in ISSUE_TAGS.items():
        if any(kw in c for c in cats):
            seen[key] = {'key': key, 'label': label}
    return list(seen.values())


def find_watchlist_tasks(items):
    """
    items: [{title, count}] — articles the user has edited repeatedly. Flags ones that
    have since picked up maintenance-issue tags (unreferenced, orphan, citation-needed,
    cleanup, disputed, stale) since the user last worked on them.
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
            tags = _tags_from_categories(cats)
            if tags:
                count = count_map.get(title, 0)
                tasks.append({
                    'title': title,
                    'source': 'watchlist',
                    'tags': tags,
                    'reason': f'You edited this {count}× — ' + ', '.join(t['label'] for t in tags),
                })
    return tasks


def find_followup_tasks(titles):
    """
    titles: articles the user created. Flags ones still in rough shape — still a stub,
    still unreferenced/orphaned/etc, or short enough to be worth expanding.
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
            tags = _tags_from_categories(cats)
            is_stub = any('stub' in c for c in cats)
            if is_stub:
                tags.append({'key': 'stub', 'label': 'Stub'})

            length = pg.get('length') or 99999
            is_short = length < 4000
            if is_short and not is_stub:
                tags.append({'key': 'expand', 'label': 'Could be expanded'})

            if not tags:
                continue

            tasks.append({
                'title': title,
                'source': 'followup',
                'tags': tags,
                'reason': 'You created this article — ' + ', '.join(t['label'] for t in tags),
            })
    return tasks
