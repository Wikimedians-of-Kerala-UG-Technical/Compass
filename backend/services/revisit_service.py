"""Revisit: the editor's own articles (created or heavily edited) that need attention.

For each article: which maintenance tags it carries (with the tag's date from the
dated tracking category), whether a tag appeared after the editor's last edit there,
machine suggestions (Growth "add an image"), and whether its latest revision, made by
someone else, looks like possible vandalism (Lift Wing revert-risk model).
"""
from concurrent.futures import ThreadPoolExecutor

from services import wiki, maintenance
from services.signals import article_signals, dated_tags
from services.task_service import DATED_ISSUE

REVERT_RISK_URL = 'https://api.wikimedia.org/service/lw/inference/v1/models/revertrisk-language-agnostic:predict'
REVERT_RISK_THRESHOLD = 0.9
WEAK = {'stub', 'add_link'}
SHORTDESC_CATEGORY = 'Articles with short description'


def _latest_revisions(dbname, titles):
    """title -> {user, timestamp, revid} of the latest revision (batched, 50 per call)."""
    out = {}
    for page in wiki.api_pages(dbname, titles, {
        'action': 'query', 'prop': 'revisions', 'rvprop': 'user|timestamp|ids',
    }):
        revs = page.get('revisions') or []
        if revs:
            out[page['title']] = revs[0]
    return out


def _revert_risk(dbname, revid):
    data = wiki.post_json(REVERT_RISK_URL, {'rev_id': revid, 'lang': wiki.lang(dbname)}, retries=2, timeout=10)
    try:
        return data['output']['probabilities']['true']
    except (KeyError, TypeError):
        return None


def find_revisit(profile, watched=None):
    """`watched`: titles from the editor's watchlist (logged-in only), checked as well."""
    dbname = profile['homeWiki']
    username = profile['username']
    last_edit = profile.get('_lastEdit') or {}
    created = profile.get('createdArticles') or []
    heavy = {h['title']: h for h in profile.get('heavilyEdited') or []}
    watched = list(watched or [])
    titles = list(dict.fromkeys(created + list(heavy) + watched))
    sigs = article_signals(dbname, titles)
    latest = _latest_revisions(dbname, [t for t in titles if t in sigs])

    items = []
    for title in titles:
        sig = sigs.get(title)
        if not sig:
            continue
        issues = maintenance.issues_of(dbname, sig)
        dated = {DATED_ISSUE[k]: v for k, v in dated_tags(sig['categories']).items() if k in DATED_ISSUE}
        mine = last_edit.get(title)
        tags = []
        for key in issues:
            since = dated.get(key)
            tags.append({
                'key': key,
                'label': maintenance.meta(key)['short'],
                'since': since,
                # A dated tag is "new" when its month is after the month of the editor's last edit.
                'newSinceYourEdit': bool(since and mine and since > mine[:7]),
            })
        if dbname == 'enwiki' and SHORTDESC_CATEGORY not in sig['categories']:
            tags.append({'key': 'shortdesc', 'label': 'No short description', 'since': None, 'newSinceYourEdit': False})
        rev = latest.get(title) or {}
        items.append({
            'title': title,
            'wiki': dbname,
            'url': wiki.page_url(dbname, title),
            'editUrl': wiki.edit_url(dbname, title),
            'source': 'created' if title in created else 'edited' if title in heavy else 'watched',
            'editCount': heavy.get(title, {}).get('count'),
            'yourLastEdit': mine,
            'lastEdit': {'user': rev.get('user'), 'timestamp': rev.get('timestamp'), 'revid': rev.get('revid')},
            'quality': sig.get('quality'),
            'size': sig.get('bytes'),
            'tags': tags,
        })

    # Possible vandalism: the latest revision is by someone else and the model is confident.
    to_check = [i for i in items if i['lastEdit']['revid'] and i['lastEdit']['user'] != username][:40]
    with ThreadPoolExecutor(max_workers=10) as pool:
        for item, risk in zip(to_check, pool.map(lambda i: _revert_risk(dbname, i['lastEdit']['revid']), to_check)):
            item['lastEdit']['revertRisk'] = round(risk, 3) if risk is not None else None
            if risk is not None and risk >= REVERT_RISK_THRESHOLD:
                item['tags'].insert(0, {
                    'key': 'check_edit', 'label': 'Check latest edit', 'since': item['lastEdit']['timestamp'][:10],
                    'newSinceYourEdit': True,
                })

    out = []
    for item in items:
        if not item['tags']:
            continue
        strong = [t for t in item['tags'] if t['key'] not in WEAK and t['key'] != 'shortdesc']
        item['weak'] = not strong
        item['hasNew'] = any(t['newSinceYourEdit'] for t in item['tags'])
        labels = ', '.join(t['label'] for t in item['tags'])
        who = ('You created this article' if item['source'] == 'created'
               else f'You edited this {item["editCount"]}×' if item['source'] == 'edited'
               else 'On your watchlist')
        item['reason'] = f'{who} — {labels}'
        out.append(item)
    out.sort(key=lambda i: (not i['hasNew'], i['weak'], -len(i['tags'])))
    return {'wiki': dbname, 'checked': len(titles), 'tasks': out}
