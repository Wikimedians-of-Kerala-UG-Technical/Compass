"""Where an editor works, from Wikidata place hierarchies (P131 "located in").

For each edited article that is about a place (or a person, via their birthplace),
walks P131 up to the country and counts every level: Kochi -> Ernakulam district ->
Kerala -> India. Statements are read by rank (preferred first, deprecated skipped), and
dissolved entities (P576, e.g. "Kingdom of Great Britain") are skipped, so historical
states don't become someone's "focus".
"""
from concurrent.futures import ThreadPoolExecutor

from services import wiki
from services.signals import article_signals

MAX_HOPS = 6
HUMAN_QID = 'Q5'
_claims_cache = wiki.TTLCache(ttl=7 * 24 * 3600, maxsize=50000, name='wikidata-places')
_geo_cache = wiki.TTLCache(ttl=6 * 3600, maxsize=500, name='geo')


def _targets(claims, prop):
    """Item ids a property points to, preferred rank first, deprecated skipped."""
    stmts = [s for s in claims.get(prop, []) if s.get('rank') != 'deprecated']
    stmts.sort(key=lambda s: s.get('rank') != 'preferred')
    out = []
    for s in stmts:
        try:
            out.append(s['mainsnak']['datavalue']['value']['id'])
        except (KeyError, TypeError):
            continue
    return out


def _coord(claims):
    for s in claims.get('P625', []):
        try:
            v = s['mainsnak']['datavalue']['value']
            return {'lat': v['latitude'], 'lon': v['longitude']}
        except (KeyError, TypeError):
            continue
    return None


def _fetch_claims(qids, language):
    need = [q for q in dict.fromkeys(qids) if q and _claims_cache.get((q, language)) is None]
    # Batches of 20, a few in parallel: a state or country item is ~1 MB of claims, so
    # one 50-item batch can take several seconds. wiki.py caps Wikidata concurrency.
    batches = [need[i:i + 20] for i in range(0, len(need), 20)]

    def fetch(batch):
        return wiki.api('wikidatawiki', {
            'action': 'wbgetentities', 'ids': '|'.join(batch), 'props': 'claims|labels',
            'languages': f'{language}|en', 'languagefallback': 1,
        }, post=True)

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(fetch, batches))
    for data in results:
        for qid, entity in (data.get('entities') or {}).items():
            claims = entity.get('claims') or {}
            labels = entity.get('labels') or {}
            label = (labels.get(language) or labels.get('en') or {}).get('value')
            _claims_cache.set((qid, language), {
                'label': label,
                'labelEn': (labels.get('en') or {}).get('value'),
                'is_country': 'P297' in claims,
                'is_admin1': 'P300' in claims,
                'is_human': HUMAN_QID in _targets(claims, 'P31'),
                'dissolved': 'P576' in claims,
                'populated': 'P1082' in claims,
                'coord': _coord(claims),
                'p131': _targets(claims, 'P131'),
                'p17': _targets(claims, 'P17'),
                'p19': _targets(claims, 'P19'),
                'p27': _targets(claims, 'P27'),
            })
    return {q: _claims_cache.get((q, language)) for q in qids if _claims_cache.get((q, language))}


def _parent(info, language, exclude=()):
    """The place one level up. An item can have several best-rank P131 values (a
    village listed in its old and new district); a dissolved one is the last choice."""
    parents = [p for p in (info['p131'] or info['p17']) if p not in exclude]
    live = [p for p in parents if not (_claims_cache.get((p, language)) or {}).get('dissolved')]
    return (live or parents or [None])[0]


def _anchor(qid, info):
    """Where to start walking, and whether the article's own label counts as a place.
    People start at their birthplace (else citizenship). Other subjects only count if
    they sit in a place hierarchy; a building (no population) contributes its parents,
    not its own name, so "Kerala Soil Museum" isn't reported as a place."""
    if not info:
        return None, False
    if info['is_human']:
        if info['p19']:
            return info['p19'][0], True
        if info['p27']:
            return info['p27'][0], True
        return None, False
    if info['is_country'] or info['is_admin1']:
        return qid, True
    if info['p131']:
        return qid, info['populated']
    return None, False


def resolve_geo(dbname, titles):
    """Returns {places: [{qid,name,count,coord,level}], countries: [...], articlesWithGeo, focus}."""
    key = (dbname, tuple(sorted(titles)))
    return _geo_cache.get_or_compute(key, lambda: _resolve(dbname, titles))


def _maybe_geo(sig):
    """Could this article be about a place, or a person with a birthplace? Decided from
    the signals the profile already loaded, so Compass doesn't download full Wikidata
    items for, say, 150 drug and disease articles to find 9 places. Articles without
    signals are kept. Only items in a P131 hierarchy, or people, count (see `_anchor`),
    and those nearly always have coordinates, a country label or a geography/biography
    topic. (Coordinates and topics alone missed 12 of Ranjithsiji's 88 places.)"""
    if sig is None:
        return True
    return bool(sig['coord'] or sig['countries']) or any(t.startswith(('Geography.', 'Culture.Biography')) for t in sig['topics'])


def _resolve(dbname, titles):
    language = wiki.lang(dbname)
    sigs = article_signals(dbname, titles)  # cached by the profile
    titles = [t for t in titles if _maybe_geo(sigs.get(t))]
    qid_of = {}
    params = {'action': 'query', 'prop': 'pageprops', 'ppprop': 'wikibase_item'}
    batches = [titles[i:i + 50] for i in range(0, len(titles), 50)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for pages in pool.map(lambda b: list(wiki.api_pages(dbname, b, params)), batches):
            for page in pages:
                q = (page.get('pageprops') or {}).get('wikibase_item')
                if q:
                    qid_of[page['title']] = q
    infos = _fetch_claims(list(qid_of.values()), language)

    anchors = {}
    for title, q in qid_of.items():
        a, include_self = _anchor(q, infos.get(q))
        if a:
            anchors[title] = (a, include_self)
    # Fetch the hierarchy one level at a time, in parallel batches, before walking it.
    known = {a for a, _ in anchors.values()}
    frontier = set(known)
    for _ in range(MAX_HOPS):
        batch = _fetch_claims(list(frontier), language)
        nxt = set()
        for q in frontier:
            info = batch.get(q)
            if not info or info['is_country']:
                continue
            parent = _parent(info, language)
            if parent and parent not in known:
                known.add(parent)
                nxt.add(parent)
        if not nxt:
            break
        frontier = nxt

    chain_cache = {}

    def chain(start):
        if start in chain_cache:
            return chain_cache[start]
        path, current = [], start
        for _ in range(MAX_HOPS):
            info = _fetch_claims([current], language).get(current)
            if not info:
                break
            path.append(current)
            if info['is_country']:
                break
            current = _parent(info, language, exclude=path)
            if not current:
                break
        chain_cache[start] = path
        return path

    place_counts, place_level = {}, {}
    country_counts = {}
    article_nodes = []
    with_geo = 0
    for title, (anchor, include_self) in anchors.items():
        path = chain(anchor)
        if not include_self and path and path[0] == qid_of[title]:
            path = path[1:]
        nodes = []
        for depth, q in enumerate(path):
            info = _fetch_claims([q], language).get(q)
            if not info or info['dissolved'] or not info['label']:
                continue
            nodes.append(q)
            place_level[q] = 'country' if info['is_country'] else 'admin1' if info['is_admin1'] else 'local'
        if not nodes:
            continue
        article_nodes.append(nodes)
        with_geo += 1
        for q in set(nodes):
            place_counts[q] = place_counts.get(q, 0) + 1
            if place_level[q] == 'country':
                country_counts[q] = country_counts.get(q, 0) + 1

    def describe(q, count):
        info = _fetch_claims([q], language)[q]
        return {'qid': q, 'name': info['label'], 'nameEn': info['labelEn'], 'count': count,
                'level': place_level[q], 'coord': info['coord']}

    places = [describe(q, c) for q, c in sorted(place_counts.items(), key=lambda kv: kv[1], reverse=True)]
    countries = [p for p in places if p['level'] == 'country']
    # A focus has to be a real share of everything the editor works on, not just of the
    # few articles that happen to be about places (2 of Doc James's 9 geo articles were
    # in Kentucky, out of ~200 analysed).
    threshold = max(3, round(0.03 * len(titles)))
    sub_national = [p for p in places if p['level'] != 'country' and p['count'] >= threshold]
    region = next((p for p in sub_national if p['level'] == 'admin1'), None) or (sub_national[0] if sub_national else None)
    # The most-edited local place *inside* the focus region (a district or city), used
    # for "near where you edit" search.
    local = None
    if region:
        inside = {}
        for nodes in article_nodes:
            if region['qid'] in nodes:
                # Only places *below* the region in this chain (district, city).
                for q in nodes[:nodes.index(region['qid'])]:
                    if place_level.get(q) == 'local':
                        inside[q] = inside.get(q, 0) + 1
        for q, c in sorted(inside.items(), key=lambda kv: kv[1], reverse=True):
            d = describe(q, place_counts[q])
            if d['coord'] and c >= 2:
                local = d
                break
    if not local and not region:
        local = next((p for p in sub_national if p['level'] == 'local' and p['coord']), None)
    return {
        'articlesWithGeo': with_geo,
        'topPlaces': [p for p in places if p['level'] != 'country'][:12],
        'topCountries': countries[:3],
        'focus': {
            'region': region,
            'local': local,
            'country': countries[0] if countries else None,
        },
    }
