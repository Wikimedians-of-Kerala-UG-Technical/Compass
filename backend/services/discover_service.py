"""Discover: articles and sections to translate into the editor's languages.

Uses the Content Translation recommendation API (the engine behind CX's own
suggestions) seeded with the editor's own articles, plus its `sections` endpoint for
articles that exist in both languages but are missing sections in the target. Gaps
in the editor's region come from the Wikidata Query Service.
"""
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode

from services import wiki

CX_API = 'https://api.wikimedia.org/service/lw/recommendation/api/v1/translation'
WDQS = 'https://query.wikidata.org/sparql'
_cache = wiki.TTLCache(ttl=6 * 3600, name='discover')
_wdqs_cache = wiki.TTLCache(ttl=24 * 3600, name='region-gaps')


def cx_url(target_db, title, source, target, section=None):
    params = {'page': title, 'from': source, 'to': target}
    if section:
        params['sourcesection'] = section
    return f'https://{wiki.host(target_db)}/wiki/Special:ContentTranslation?{urlencode(params)}'


def _language_pairs(profile):
    """(source, target) language pairs the editor can translate between: from English
    (or their home language) into each other language they read and write."""
    home = profile['homeLang']
    langs = [l['lang'] for l in profile.get('languages') or [] if l['dbname'] != 'enwiki' or l['lang'] == 'en']
    langs = list(dict.fromkeys([home] + langs))
    source = 'en' if 'en' in langs else home
    return [(source, t) for t in langs if t != source][:3]


def _seeds(profile, source):
    """The editor's most-edited articles, as titles on the source wiki."""
    home_db = profile['homeWiki']
    titles = [h['title'] for h in profile.get('heavilyEdited') or []][:8] or (profile.get('_editedTitles') or [])[:8]
    if wiki.lang(home_db) == source:
        return titles[:5]
    mapped = []
    for page in wiki.api_pages(home_db, titles, {'action': 'query', 'prop': 'langlinks', 'lllang': source}):
        links = page.get('langlinks') or []
        if links:
            mapped.append(links[0]['title'])
    return mapped[:5]


def _cx(path, params):
    data = wiki.get_json(f'{CX_API}{path}', params=params, retries=2, timeout=60)
    return (data or {}).get('recommendations') or []


def region_gaps(place_qids, target_lang, limit=20):
    """Wikidata items located directly in the editor's places (their district and state)
    that have an English article but none in the target language, most widely covered
    first. Only direct P131 children: transitive paths (P131+) over a whole state time
    out on the Query Service. Cached for a day."""
    place_qids = tuple(q for q in place_qids if q)
    if not place_qids:
        return []

    def compute():
        query = f'''
SELECT ?item ?itemLabel ?enTitle ?links WHERE {{
  VALUES ?place {{ {' '.join('wd:' + q for q in place_qids)} }}
  ?item wdt:P131 ?place; wikibase:sitelinks ?links.
  ?en schema:about ?item; schema:isPartOf <https://en.wikipedia.org/>; schema:name ?enTitle.
  FILTER NOT EXISTS {{ ?t schema:about ?item; schema:isPartOf <https://{wiki.host(target_lang.replace('-', '_') + 'wiki')}/> }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}} ORDER BY DESC(?links) LIMIT {limit}'''
        data = wiki.get_json(WDQS, params={'query': query, 'format': 'json'}, retries=1, timeout=60)
        rows = ((data or {}).get('results') or {}).get('bindings') or []
        return [{
            'qid': r['item']['value'].rsplit('/', 1)[1],
            'title': r['enTitle']['value'],
            'label': r['itemLabel']['value'],
            'sitelinks': int(r['links']['value']),
        } for r in rows]
    try:
        return _wdqs_cache.get_or_compute((place_qids, target_lang, limit), compute)
    except Exception:
        return []


def find_discover(profile, region=None):
    key = (profile['username'], profile['homeWiki'], (region or {}).get('qid'), (region or {}).get('localQid'))
    return _cache.get_or_compute(key, lambda: _discover(profile, region))


def _discover(profile, region):
    t0 = time.time()
    pairs = _language_pairs(profile)
    if not pairs:
        return {
            'monolingual': True, 'pairs': [], 'articles': [], 'sections': [], 'regionGaps': [],
            'languages': profile.get('languages') or [], 'secs': round(time.time() - t0, 1),
        }
    topics = [t['slug'] for t in profile.get('topics') or []][:2]
    country = (profile.get('countries') or [{}])[0].get('a3')
    articles, sections, gaps, failed = [], [], [], []

    def work(pair):
        source, target = pair
        target_db = target.replace('-', '_') + 'wiki'
        seeds = _seeds(profile, source)
        out_a, out_s = [], []
        calls = []
        if seeds:
            calls.append(('seed', {'source': source, 'target': target, 'seed': '|'.join(seeds), 'count': 24}))
        for t in topics:
            p = {'source': source, 'target': target, 'topic': t, 'count': 12}
            if country:
                p['country'] = country
            calls.append((f'topic:{t}', p))
        for why, params in calls:
            try:
                for r in _cx('', params):
                    out_a.append({
                        'title': r['title'], 'qid': r.get('wikidata_id'), 'source': source, 'target': target,
                        'languages': r.get('langlinks_count', 0), 'size': r.get('size', 0),
                        'why': (f'Related to {", ".join(seeds[:2])}' if why == 'seed'
                                else f'Popular in {why.split(":", 1)[1].replace("-", " ")}'
                                + (f' · {country.upper()}' if country else '')),
                        'sourceUrl': wiki.page_url(source.replace('-', '_') + 'wiki', r['title']),
                        'translateUrl': cx_url(target_db, r['title'], source, target),
                    })
            except Exception as e:
                failed.append(str(e)[:200])
        if seeds:
            try:
                for r in _cx('/sections', {'source': source, 'target': target, 'seed': '|'.join(seeds), 'count': 12}):
                    missing = r.get('missing') or {}
                    sizes = r.get('source_section_sizes') or {}
                    worth = [s for s in missing if s not in ('References', 'External links', 'See also', 'Notes',
                                                             'Further reading', 'Bibliography')]
                    if not worth:
                        continue
                    out_s.append({
                        'sourceTitle': r['source_title'], 'targetTitle': r['target_title'],
                        'source': source, 'target': target,
                        'missing': [{'section': s, 'targetHeading': missing[s], 'size': sizes.get(s, 0),
                                     'translateUrl': cx_url(target_db, r['source_title'], source, target, s)}
                                    for s in sorted(worth, key=lambda s: -sizes.get(s, 0))],
                        'targetUrl': wiki.page_url(target_db, r['target_title']),
                    })
            except Exception as e:
                failed.append(str(e)[:200])
        return out_a, out_s

    with ThreadPoolExecutor(max_workers=3) as pool:
        for a, s in pool.map(work, pairs):
            articles += a
            sections += s

    # Within each source (related to your articles / popular in your topic), the most
    # widely covered first; then alternate sources so both kinds show up.
    groups = {}
    for a in articles:
        groups.setdefault(a['why'], []).append(a)
    for g in groups.values():
        g.sort(key=lambda a: (-a['languages'], -a['size']))
    seen, ranked = set(), []
    for i in range(max((len(g) for g in groups.values()), default=0)):
        for g in groups.values():
            if i < len(g) and (g[i]['title'], g[i]['target']) not in seen:
                seen.add((g[i]['title'], g[i]['target']))
                ranked.append(g[i])

    if region and pairs:
        target = pairs[0][1] if pairs[0][0] == 'en' else None
        if target:
            for g in region_gaps([region.get('localQid'), region.get('qid')], target):
                target_db = target.replace('-', '_') + 'wiki'
                gaps.append({**g, 'target': target, 'region': region.get('name'),
                             'translateUrl': cx_url(target_db, g['title'], 'en', target),
                             'sourceUrl': wiki.page_url('enwiki', g['title'])})

    return {
        'monolingual': False,
        'pairs': [{'source': s, 'target': t} for s, t in pairs],
        'languages': profile.get('languages') or [],
        'articles': ranked[:60],
        'sections': sections[:30],
        'regionGaps': gaps,
        'partial': bool(failed),
        'secs': round(time.time() - t0, 1),
    }
