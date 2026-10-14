"""Editor profile, built on the editor's home Wikipedia (not just enwiki).

Topics and countries come from Wikipedia's own ML labels on the articles the editor
works on (`cirrusdoc` weighted_tags), so they work in every language and for every
subject, instead of a hand-written keyword list.
"""
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor

from services import wiki
from services.signals import article_signals, aggregate_profile, topic_label, topic_slug, \
    is_region_topic, country_info

CONTRIBS_LIMIT = 2000
SIGNAL_ARTICLES = 200
CREATIONS_LIMIT = 1000
LANGUAGE_MIN_EDITS = 100

_profiles = wiki.TTLCache(ttl=6 * 3600, maxsize=500)
_globals = wiki.TTLCache(ttl=6 * 3600, maxsize=500)

REVERT_TAGS = ('mw-rollback', 'mw-undo', 'mw-manual-revert')


def fetch_global_user(username):
    """globaluserinfo: global edit count and per-wiki edit counts."""
    def compute():
        data = wiki.api('metawiki', {
            'action': 'query', 'meta': 'globaluserinfo', 'guiuser': username, 'guiprop': 'merged|editcount',
        })
        info = (data.get('query') or {}).get('globaluserinfo') or {}
        if info.get('missing') is not None or not info.get('merged'):
            raise ValueError(f'No Wikimedia account named "{username}".')
        per_wiki = {}
        for w in info.get('merged') or []:
            db = w.get('wiki')
            if w.get('editcount', 0) > 0:
                per_wiki[db] = {'dbname': db, 'url': w.get('url'), 'editcount': w.get('editcount', 0)}
        return {'name': info.get('name', username), 'editcount': info.get('editcount', 0), 'wikis': per_wiki}
    return _globals.get_or_compute(username, compute)


def content_wikis(global_user, min_edits=1):
    """The user's Wikipedias (no Commons/Wikidata/test wikis), most edits first."""
    wikis = [w for db, w in global_user['wikis'].items()
             if wiki.is_content_wikipedia(db) and wiki.dbname_from_url(w['url']) == db
             and w['editcount'] >= min_edits]
    for w in wikis:
        w['lang'] = wiki.lang(w['dbname'])
    return sorted(wikis, key=lambda w: w['editcount'], reverse=True)


def home_wiki(global_user):
    wikis = content_wikis(global_user)
    return wikis[0]['dbname'] if wikis else 'enwiki'


def fetch_contribs(dbname, username, limit=CONTRIBS_LIMIT, namespace=None, show=None,
                   prop='title|timestamp|comment|sizediff|tags|size|ids|flags'):
    out, cont = [], None
    while len(out) < limit:
        params = {
            'action': 'query', 'list': 'usercontribs', 'ucuser': username,
            'uclimit': min(500, limit - len(out)), 'ucprop': prop, 'ucdir': 'older',
        }
        if namespace is not None:
            params['ucnamespace'] = namespace
        if show:
            params['ucshow'] = show
        if cont:
            params['uccontinue'] = cont
        data = wiki.api(dbname, params)
        batch = (data.get('query') or {}).get('usercontribs') or []
        out.extend(batch)
        cont = (data.get('continue') or {}).get('uccontinue')
        if not batch or not cont:
            break
    return out


def fetch_babel(dbname, username):
    try:
        data = wiki.api(dbname, {'action': 'query', 'meta': 'babel', 'babuser': username})
        return (data.get('query') or {}).get('babel') or {}
    except Exception:
        return {}


def fetch_categories(dbname, titles):
    """Visible (non-hidden) categories of each title."""
    cat_map = {}
    for page in wiki.api_pages(dbname, titles, {
        'action': 'query', 'prop': 'categories', 'cllimit': 'max', 'clshow': '!hidden',
    }):
        cat_map[page['title']] = [c['title'].split(':', 1)[1] for c in page.get('categories') or []]
    return cat_map


# Maintenance/tracking categories that some wikis don't mark as hidden.
NON_TOPICAL = re.compile(
    r'(CS1|Pages (using|with)|Articles (with|containing|needing|lacking)|^All |Wikipedia|Webarchive|'
    r'^Use |Short description|Coordinates|Commons category|Wikidata|stub|template|\(\w{2,3}(-\w+)?\)$)',
    re.IGNORECASE)
MEGA_CATEGORY = 5000
ADMIN_CATEGORY = 'Q15647814'  # Wikidata: Wikimedia administration category


GENERIC_CATEGORIES = ['Living people', 'Possibly living people', 'Year of birth missing (living people)']
_generic_cache = wiki.TTLCache(ttl=7 * 24 * 3600)


def generic_categories(dbname):
    """Local names of categories that hold everyone (e.g. ml: ജീവിച്ചിരിക്കുന്നവർ)."""
    from services.maintenance import _local_names
    return _generic_cache.get_or_compute(
        dbname, lambda: list(_local_names(dbname, 'Category', GENERIC_CATEGORIES).values()))


def topical_categories(dbname, cat_counts, cat_weight=None, limit=15):
    """The user's categories, minus tracking ones and ones that hold everyone.

    Uses each category's Wikidata item, which works in any language: categories that
    say what they're about (P301 main topic, or P4224 "contains") rank first; births and
    deaths categories (P4224 human with a P569/P570 qualifier) and Wikimedia administration
    (maintenance) categories (P31 Q15647814) are dropped. Categories
    with no Wikidata item at all are often local maintenance categories (tawiki's
    "articles needing wikification" isn't hidden), so they rank last. Categories over
    5,000 pages are dropped too.
    """
    generic = set(generic_categories(dbname))
    cat_weight = cat_weight or cat_counts
    ranked = [(c, k) for c, k in sorted(cat_counts.items(), key=lambda kv: cat_weight[kv[0]], reverse=True)
              if k >= 2 and not NON_TOPICAL.search(c) and c not in generic][:40]
    sizes, items = {}, {}
    for page in wiki.api_pages(dbname, [f'Category:{c}' for c, _ in ranked], {
        'action': 'query', 'prop': 'categoryinfo|pageprops', 'ppprop': 'wikibase_item',
    }):
        name = page['title'].split(':', 1)[1]
        sizes[name] = (page.get('categoryinfo') or {}).get('pages', 0)
        q = (page.get('pageprops') or {}).get('wikibase_item')
        if q:
            items[name] = q
    kinds = {}
    qids = list(set(items.values()))
    for i in range(0, len(qids), 50):
        data = wiki.api('wikidatawiki', {'action': 'wbgetentities', 'ids': '|'.join(qids[i:i + 50]), 'props': 'claims'}, post=True)
        for qid, ent in (data.get('entities') or {}).items():
            claims = ent.get('claims') or {}
            people_by_date = any(set(s.get('qualifiers') or {}) & {'P569', 'P570'} for s in claims.get('P4224', []))
            admin = any(((s.get('mainsnak') or {}).get('datavalue') or {}).get('value', {}).get('id') == ADMIN_CATEGORY
                        for s in claims.get('P31', []))
            kinds[qid] = ('skip' if people_by_date or admin
                          else 'topical' if ('P301' in claims or 'P4224' in claims) else 'plain')
    weight = {'topical': 1.0, 'plain': 0.7, None: 0.4}
    out = []
    for c, k in ranked:
        kind = kinds.get(items.get(c))
        if kind == 'skip' or sizes.get(c, 0) > MEGA_CATEGORY:
            continue
        out.append({'name': c, 'count': k, 'size': sizes.get(c, 0), 'rank': cat_weight[c] * weight.get(kind, 0.4)})
    out.sort(key=lambda x: x['rank'], reverse=True)
    return [{k: v for k, v in x.items() if k != 'rank'} for x in out[:limit]]


def classify_edit(contrib):
    """Edit type from MediaWiki change tags first (language-independent), then from the
    edit summary (English-only heuristics), then from the size of the change."""
    tags = contrib.get('tags') or []
    ns = contrib.get('ns') or 0
    if any(t in REVERT_TAGS for t in tags):
        return 'revert'
    if any(t.startswith('contenttranslation') for t in tags):
        return 'translation'
    if any(t.startswith('newcomer task') for t in tags):
        return 'newcomer_task'
    if 'mw-new-redirect' in tags or 'mw-changed-redirect-target' in tags:
        return 'redirect'
    if ns != 0:
        if ns % 2 == 1 or ns == 4:
            return 'discussion'
        if ns == 14:
            return 'categorization'
        if ns == 6:
            return 'media'
        if ns == 10:
            return 'template'
        return 'other_namespace'
    if 'editcheck-newreference' in tags:
        return 'references'
    c = (contrib.get('comment') or '').lower()
    sizediff = contrib.get('sizediff') or 0
    if contrib.get('new') is not None:
        return 'creation'
    if re.search(r'copyedit|copy edit|grammar|spelling|typo', c):
        return 'copyedit'
    if re.search(r'categor|recat|hotcat', c):
        return 'categorization'
    if re.search(r'\bref|citation|source|\bcite\b', c):
        return 'references'
    if re.search(r'image|file:|photo', c):
        return 'media'
    if re.search(r'infobox|template|navbox', c):
        return 'template'
    if re.search(r'\blink|orphan|dead.?end', c):
        return 'linking'
    if re.search(r'short desc', c) or 'shortdesc helper' in tags:
        return 'shortdesc'
    if sizediff > 500:
        return 'major_add'
    if sizediff < -500:
        return 'major_remove'
    if abs(sizediff) < 50:
        return 'minor'
    return 'general'


def reverted_by_others(contribs):
    """Share of the user's article edits that were reverted by someone else.
    `mw-reverted` also marks edits the user undid themselves, so an edit counts as
    self-reverted when the user's own next edit on that page is a revert."""
    by_title = {}
    for c in reversed(contribs):  # oldest first
        by_title.setdefault(c['title'], []).append(c)
    reverted = 0
    for edits in by_title.values():
        for i, c in enumerate(edits):
            if 'mw-reverted' not in (c.get('tags') or []):
                continue
            nxt = edits[i + 1] if i + 1 < len(edits) else None
            if nxt and any(t in REVERT_TAGS for t in nxt.get('tags') or []):
                continue
            reverted += 1
    total = len(contribs)
    return {'count': reverted, 'of': total, 'share': round(reverted / total, 4) if total else 0}


def build_profile(username, dbname=None):
    key = (username, dbname)
    return _profiles.get_or_compute(key, lambda: _build_profile(username, dbname))


def _build_profile(username, dbname):
    t0 = time.time()
    gu = fetch_global_user(username)
    wikis = content_wikis(gu)
    home = dbname or home_wiki(gu)
    pool = ThreadPoolExecutor(max_workers=4)
    created_f = pool.submit(fetch_contribs, home, username, CREATIONS_LIMIT, 0, 'new', 'title|timestamp')
    babel_f = pool.submit(fetch_babel, home, username)
    contribs = fetch_contribs(home, username)
    if not contribs:
        raise ValueError(f'"{username}" has no edits on {home}.')

    articles = [c for c in contribs if (c.get('ns') or 0) == 0]
    page_counts, last_edit = {}, {}
    for c in articles:
        page_counts[c['title']] = page_counts.get(c['title'], 0) + 1
        last_edit.setdefault(c['title'], c['timestamp'])  # contribs are newest first
    recent_titles = list(dict.fromkeys(c['title'] for c in articles))
    by_count = sorted(page_counts, key=page_counts.get, reverse=True)
    signal_titles = list(dict.fromkeys(by_count[:50] + recent_titles))[:SIGNAL_ARTICLES]

    cats_f = pool.submit(fetch_categories, home, signal_titles[:150])
    sigs = article_signals(home, signal_titles)
    # Articles the editor keeps coming back to say more about them than one-off edits
    # (patrolling, typo fixes), so each article counts 1 + log2(edits on it).
    weights = {t: 1 + math.log2(page_counts.get(t, 1)) for t in signal_titles}
    present = [sigs[t] for t in signal_titles if t in sigs]
    topic_w, country_w = aggregate_profile(present, [weights[s['title']] if s['title'] in weights else 1 for s in present])
    n = max(sum(weights.get(s['title'], 1) for s in present), 1)
    topics = [
        {'path': p, 'slug': topic_slug(p), 'label': topic_label(p), 'share': round(w / n, 3)}
        for p, w in sorted(topic_w.items(), key=lambda kv: kv[1], reverse=True)
        if not is_region_topic(p) and w / n >= 0.05
    ][:6]
    regions = [
        {'path': p, 'slug': topic_slug(p), 'label': topic_label(p), 'share': round(w / n, 3)}
        for p, w in sorted(topic_w.items(), key=lambda kv: kv[1], reverse=True)
        if is_region_topic(p) and not p.endswith('*') and w / n >= 0.05
    ][:4]
    countries = []
    for name, w in sorted(country_w.items(), key=lambda kv: kv[1], reverse=True):
        info = country_info(name)
        if info and w / n >= 0.05:
            countries.append({**info, 'share': round(w / n, 3)})
    countries = countries[:4]

    cat_map = cats_f.result()
    cat_counts, cat_weight = {}, {}
    for title, cats in cat_map.items():
        for cat in cats:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            cat_weight[cat] = cat_weight.get(cat, 0) + weights.get(title, 1)
    top_categories = topical_categories(home, cat_counts, cat_weight)

    created = created_f.result()
    created_live = [c['title'] for c in created]

    edit_types = {}
    for c in contribs:
        t = classify_edit(c)
        edit_types[t] = edit_types.get(t, 0) + 1

    babel = babel_f.result()
    pool.shutdown()
    languages = {}
    for code, level in babel.items():
        languages[code] = {'lang': code, 'level': level, 'source': 'babel'}
    # Babel is what the editor says they can read and write. Edit counts are only a
    # fallback: medical translators, interwiki fixers and bots edit dozens of wikis.
    if not any(level not in ('0', '1') for level in babel.values()):
        for w in wikis[:4]:
            if w['editcount'] >= LANGUAGE_MIN_EDITS and w['lang'] not in languages:
                languages[w['lang']] = {'lang': w['lang'], 'level': None, 'source': 'edits'}
    languages.setdefault(wiki.lang(home), {'lang': wiki.lang(home), 'level': None, 'source': 'home'})
    for code, entry in languages.items():
        db = code.replace('-', '_') + 'wiki'
        w = gu['wikis'].get(db)
        entry['dbname'] = db
        entry['editcount'] = w['editcount'] if w else 0
        entry['url'] = f'https://{wiki.host(db)}'
    language_list = sorted(
        (l for l in languages.values() if l['level'] not in ('0', '1')),
        key=lambda l: (l['dbname'] != home, -l['editcount']))

    heavily = [
        {'title': t, 'count': page_counts[t], 'lastEdit': last_edit[t]}
        for t in by_count if page_counts[t] >= 3
    ][:15]

    sister = {db: gu['wikis'][db]['editcount'] for db in ('wikidatawiki', 'commonswiki') if db in gu['wikis']}

    return {
        'username': gu['name'],
        'homeWiki': home,
        'homeLang': wiki.lang(home),
        'homeUrl': f'https://{wiki.host(home)}',
        'wikis': [{k: w[k] for k in ('dbname', 'lang', 'url', 'editcount')} for w in wikis[:12]],
        'languages': language_list,
        'total': gu['editcount'],
        'homeEdits': gu['wikis'].get(home, {}).get('editcount', len(contribs)),
        'sisterProjects': sister,
        'editsAnalysed': len(contribs),
        'uniqueArticles': len(page_counts),
        'topics': topics,
        'regions': regions,
        'countries': countries,
        'topTopics': [t['label'] for t in topics[:3]] or ['general'],
        'topCategories': top_categories,
        'editTypes': edit_types,
        'reverted': reverted_by_others(articles),
        'heavilyEdited': heavily,
        'createdArticles': created_live[:50],
        'createdCount': len(created_live),
        'createdCountCapped': len(created_live) >= CREATIONS_LIMIT,
        'recentEdits': [
            {
                'title': c['title'],
                'timestamp': c.get('timestamp'),
                'comment': c.get('comment') or '',
                'sizediff': c.get('sizediff', 0),
                'diffUrl': f"https://{wiki.host(home)}/w/index.php?diff={c['revid']}" if c.get('revid') else None,
                'articleUrl': wiki.page_url(home, c['title']),
            }
            for c in contribs[:15]
        ],
        '_editedTitles': signal_titles,
        '_lastEdit': last_edit,
        'secs': round(time.time() - t0, 1),
    }


def public_profile(profile):
    """Profile without the internal fields other services reuse."""
    return {k: v for k, v in profile.items() if not k.startswith('_')}
