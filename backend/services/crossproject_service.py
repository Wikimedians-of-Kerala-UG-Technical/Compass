"""Tasks on Commons and Wikidata, for editors whose work is mostly there.

- Place your photos: the editor's recent Commons uploads that no Wikipedia article
  uses yet (`globalusage`), each with candidate articles on their home wiki (by the
  photo's coordinates when it has them, else by its title).
- Wikidata gaps: items in the editor's place (district/region) that have no label or
  description in their language, most widely linked first (Wikidata Query Service).
- Campaigns: upcoming and ongoing events (Event Registration) whose worklists include the
  editor's articles.
"""
import re
import time
from concurrent.futures import ThreadPoolExecutor

from services import wiki

WDQS = 'https://query.wikidata.org/sparql'
_cache = wiki.TTLCache(ttl=6 * 3600, maxsize=300, name='contribute')
FILE_NOISE = re.compile(r'(\.[a-z0-9]{2,4}$)|(\bIMG[-_ ]?\w*)|(\b\d{6,}\b)|(\(\d+\))|[_\-]+', re.I)


def _clean_file_title(title):
    name = title.split(':', 1)[-1]
    name = FILE_NOISE.sub(' ', name)
    return re.sub(r'\s+', ' ', name).strip()


def unused_uploads(username, home_db, limit=50):
    data = wiki.api('commonswiki', {
        'action': 'query', 'list': 'allimages', 'aiuser': username, 'aisort': 'timestamp',
        'aidir': 'descending', 'ailimit': limit,
    })
    titles = [i['title'] for i in (data.get('query') or {}).get('allimages') or []]
    if not titles:
        return {'uploads': 0, 'unused': []}
    unused = []
    for page in wiki.api_pages('commonswiki', titles, {
        'action': 'query', 'prop': 'globalusage|coordinates|imageinfo', 'gunamespace': 0, 'gulimit': 'max',
        'iiprop': 'url|mime', 'iiurlwidth': 240,
    }):
        if page.get('globalusage'):
            continue
        info = (page.get('imageinfo') or [{}])[0]
        if not (info.get('mime') or '').startswith('image/') or info.get('mime') == 'image/svg+xml':
            continue  # logos and diagrams rarely belong in an article
        coords = (page.get('coordinates') or [None])[0]
        unused.append({
            'file': page['title'], 'thumb': info.get('thumburl'), 'url': info.get('descriptionurl'),
            'coord': {'lat': coords['lat'], 'lon': coords['lon']} if coords else None,
        })

    def candidates(item):
        try:
            if item['coord']:
                q = f'nearcoord:1km,{item["coord"]["lat"]},{item["coord"]["lon"]}'
            else:
                q = _clean_file_title(item['file'])
            results, _ = wiki.search(home_db, q, limit=3)
            item['articles'] = [{'title': r['title'], 'url': wiki.page_url(home_db, r['title']),
                                 'editUrl': wiki.edit_url(home_db, r['title'])} for r in results]
            item['matchedBy'] = 'location' if item['coord'] else 'title'
        except Exception:
            item['articles'] = []
        return item

    with ThreadPoolExecutor(max_workers=4) as pool:
        unused = list(pool.map(candidates, unused[:20]))
    return {'uploads': len(titles), 'unused': unused}


def wikidata_gaps(place_qid, language, limit=20):
    """Items located in `place_qid` (any depth) missing a label or description in `language`."""
    if not place_qid:
        return []
    query = f'''
SELECT ?item ?itemLabel ?links ?hasLabel WHERE {{
  ?item wdt:P131+ wd:{place_qid}; wikibase:sitelinks ?links.
  FILTER NOT EXISTS {{ ?item schema:description ?d. FILTER(lang(?d) = "{language}") }}
  OPTIONAL {{ ?item rdfs:label ?l. FILTER(lang(?l) = "{language}") }}
  BIND(BOUND(?l) AS ?hasLabel)
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,{language}". }}
}} ORDER BY DESC(?links) LIMIT {limit}'''
    data = wiki.get_json(WDQS, params={'query': query, 'format': 'json'}, retries=1, timeout=60)
    rows = ((data or {}).get('results') or {}).get('bindings') or []
    out = []
    for r in rows:
        qid = r['item']['value'].rsplit('/', 1)[1]
        has_label = r.get('hasLabel', {}).get('value') == 'true'
        out.append({
            'qid': qid, 'label': r.get('itemLabel', {}).get('value'), 'sitelinks': int(r['links']['value']),
            'missing': ['description'] + ([] if has_label else ['label']),
            'url': f'https://www.wikidata.org/wiki/{qid}',
        })
    return out


def campaign_events(home_db, titles):
    """Upcoming and ongoing events (Event Registration) whose worklist includes any of
    these articles. Read from the worklist pages, because the extension's own lookup
    only answers logged-in users."""
    from services.event_service import events_with_articles
    return events_with_articles(home_db, titles)


def find_contribute(profile, place=None):
    key = (profile['username'], profile['homeWiki'], (place or {}).get('qid'))
    return _cache.get_or_compute(key, lambda: _contribute(profile, place))


def _contribute(profile, place):
    t0 = time.time()
    home = profile['homeWiki']
    language = profile['homeLang']
    # Everything we know they work on; the worklist lookup is local, so more is free.
    titles = list(dict.fromkeys([h['title'] for h in profile.get('heavilyEdited') or []]
                                + (profile.get('createdArticles') or []) + (profile.get('_editedTitles') or [])))
    failed = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        uploads_f = pool.submit(unused_uploads, profile['username'], home)
        gaps_f = pool.submit(wikidata_gaps, (place or {}).get('qid'), language)
        events_f = pool.submit(campaign_events, home, titles)
        results = {}
        for name, f in (('commons', uploads_f), ('wikidata', gaps_f), ('events', events_f)):
            try:
                results[name] = f.result()
            except Exception:
                results[name] = {'uploads': 0, 'unused': []} if name == 'commons' else []
                failed.append(name)
    return {
        'wiki': home,
        'language': language,
        'commons': results['commons'],
        'wikidata': {'place': (place or {}).get('name'), 'items': results['wikidata']},
        'events': results['events'],
        'sisterProjects': profile.get('sisterProjects') or {},
        'partial': bool(failed),
        'failed': failed,
        'secs': round(time.time() - t0, 1),
    }
