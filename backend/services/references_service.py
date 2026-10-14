"""Sources an editor can cite, ready to paste.

Which databases are searched depends on the article's *topic* (Wikipedia's ML topic
labels), not on words in its title: medicine and biology articles get PubMed (review
articles first, per WP:MEDRS), everything gets OpenAlex and CrossRef. Results the
article already cites are dropped, and each result is turned into a `{{cite journal}}`
through Citoid, the service behind VisualEditor's "Cite" button.

Wikipedia articles are never suggested as sources (WP:CIRCULAR).
"""
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

from services import wiki
from services.article_service import analyze_article

CITOID = 'https://en.wikipedia.org/api/rest_v1/data/citation/mediawiki/'
SEMANTIC_SCHOLAR_KEY = os.environ.get('SEMANTIC_SCHOLAR_API_KEY')
MEDICAL_TOPICS = ('Medicine & Health', 'Biology')
_cache = wiki.TTLCache(ttl=6 * 3600, maxsize=500, name='sources')


def _english_title(dbname, title):
    if dbname == 'enwiki':
        return title
    for page in wiki.api_pages(dbname, [title], {'action': 'query', 'prop': 'langlinks', 'lllang': 'en'}):
        links = page.get('langlinks') or []
        if links:
            return links[0]['title']
    return title


def _clean(title):
    return re.sub(r'\s*\([^)]*\)$', '', title)  # "Dosa (food)" -> "Dosa"


def _doi(s):
    m = re.search(r'10\.\d{4,9}/[^\s"<>]+', s or '', re.I)
    return m.group(0).rstrip('.').lower() if m else None


def pubmed(query, reviews=True, n=8):
    term = f'({query}) AND review[pt] AND ("last 10 years"[dp])' if reviews else query
    data = wiki.get_json('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi',
                         params={'db': 'pubmed', 'term': term, 'retmode': 'json', 'retmax': n, 'sort': 'relevance'},
                         retries=2, timeout=20)
    ids = ((data or {}).get('esearchresult') or {}).get('idlist') or []
    if not ids:
        return []
    summ = wiki.get_json('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi',
                         params={'db': 'pubmed', 'id': ','.join(ids), 'retmode': 'json'}, retries=2, timeout=20)
    result = (summ or {}).get('result') or {}
    out = []
    for uid in ids:
        r = result.get(uid)
        if not r:
            continue
        doi = next((a['value'] for a in r.get('articleids', []) if a.get('idtype') == 'doi'), None)
        out.append({
            'title': r.get('title', '').rstrip('.'), 'year': (r.get('pubdate') or '')[:4],
            'venue': r.get('fulljournalname') or r.get('source'),
            'authors': ', '.join(a['name'] for a in (r.get('authors') or [])[:3]),
            'doi': doi.lower() if doi else None, 'pmid': uid,
            'url': f'https://pubmed.ncbi.nlm.nih.gov/{uid}/', 'source': 'PubMed' + (' (review)' if reviews else ''),
            'citations': None,
        })
    return out


def openalex(query, n=8):
    data = wiki.get_json('https://api.openalex.org/works', params={
        'search': query, 'per-page': n,
        'select': 'doi,title,publication_year,cited_by_count,primary_location,authorships,type',
    }, retries=2, timeout=20)
    out = []
    for r in (data or {}).get('results') or []:
        loc = r.get('primary_location') or {}
        out.append({
            'title': r.get('title'), 'year': str(r.get('publication_year') or ''),
            'venue': ((loc.get('source') or {}).get('display_name')),
            'authors': ', '.join(((a.get('author') or {}).get('display_name') or '') for a in (r.get('authorships') or [])[:3]),
            'doi': _doi(r.get('doi')), 'pmid': None,
            'url': r.get('doi') or loc.get('landing_page_url'), 'source': 'OpenAlex',
            'citations': r.get('cited_by_count'),
        })
    return out


def crossref(query, n=8):
    data = wiki.get_json('https://api.crossref.org/works', params={
        'query.bibliographic': query, 'rows': n,
        'select': 'title,URL,DOI,is-referenced-by-count,issued,container-title,author,score',
    }, retries=2, timeout=20)
    out = []
    for r in ((data or {}).get('message') or {}).get('items') or []:
        if (r.get('score') or 0) < 20:  # low-relevance matches are mostly title-word noise
            continue
        year = ((r.get('issued') or {}).get('date-parts') or [[None]])[0][0]
        out.append({
            'title': (r.get('title') or [''])[0], 'year': str(year or ''),
            'venue': (r.get('container-title') or [None])[0],
            'authors': ', '.join(f"{a.get('family', '')}" for a in (r.get('author') or [])[:3]),
            'doi': (r.get('DOI') or '').lower() or None, 'pmid': None,
            'url': r.get('URL'), 'source': 'CrossRef', 'citations': r.get('is-referenced-by-count'),
        })
    return out


def semantic_scholar(query, n=8):
    if not SEMANTIC_SCHOLAR_KEY:
        return []  # unauthenticated calls are rate-limited (HTTP 429) almost always
    r = wiki.session.get('https://api.semanticscholar.org/graph/v1/paper/search',
                         params={'query': query, 'limit': n, 'fields': 'title,url,citationCount,year,externalIds,venue'},
                         headers={'x-api-key': SEMANTIC_SCHOLAR_KEY}, timeout=20)
    if not r.ok:
        return []
    return [{
        'title': p.get('title'), 'year': str(p.get('year') or ''), 'venue': p.get('venue'), 'authors': '',
        'doi': ((p.get('externalIds') or {}).get('DOI') or '').lower() or None, 'pmid': None,
        'url': p.get('url'), 'source': 'Semantic Scholar', 'citations': p.get('citationCount'),
    } for p in r.json().get('data', [])]


def citoid(identifier):
    data = wiki.get_json(CITOID + quote(identifier, safe=''), retries=1, timeout=20)
    return data[0] if isinstance(data, list) and data else None


def _first(value):
    """Citoid gives some fields as lists (ISBN, ISSN) and some as space-separated strings."""
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, str):
        value = value.split(' ')[0] if value.replace('-', '').replace(' ', '').isdigit() else value
    return value or None


def _relevant(result, query):
    """Keeps a full-text-search result only if its title shares a significant word with
    the article title. OpenAlex and CrossRef match anywhere in the record, so a village
    stub otherwise gets papers about kabaddi players."""
    words = {w for w in re.findall(r'\w+', query.lower()) if len(w) >= 4}
    title = (result.get('title') or '').lower()
    return not words or any(w in title for w in words)


def cite_template(item):
    """Citoid (Zotero) JSON -> {{cite journal}} / {{cite book}} / {{cite web}} wikitext."""
    kind = item.get('itemType')
    name = 'cite journal' if kind == 'journalArticle' else 'cite book' if kind in ('book', 'bookSection') else 'cite web'
    parts = []
    for i, a in enumerate((item.get('author') or [])[:6], 1):
        if isinstance(a, list) and len(a) == 2:
            parts.append(f'last{i}={a[1]}')
            if a[0]:
                parts.append(f'first{i}={a[0]}')
    if len(item.get('author') or []) > 6:
        parts.append('display-authors=etal')
    fields = [
        ('title', item.get('title')), ('journal' if name == 'cite journal' else 'website' if name == 'cite web' else 'publisher',
                                       item.get('publicationTitle') or item.get('websiteTitle') or item.get('publisher')),
        ('date', item.get('date')), ('volume', item.get('volume')), ('issue', item.get('issue')),
        ('pages', item.get('pages')), ('doi', item.get('DOI')), ('pmid', item.get('PMID')),
        ('pmc', item.get('PMCID')), ('isbn', _first(item.get('ISBN'))),
        ('url', item.get('url') if not item.get('DOI') else None), ('access-date', item.get('accessDate')),
    ]
    parts += [f'{k}={_first(v)}' for k, v in fields if _first(v)]
    return '{{' + name + ' |' + ' |'.join(parts) + '}}'


def find_external_references(title, dbname='enwiki'):
    key = (dbname, title)
    cached = _cache.get(key)
    if cached:
        return cached
    t0 = time.time()
    guide = analyze_article(title, dbname)
    topics = guide.get('topics') or []
    query = _clean(_english_title(dbname, title))
    medical = any(t in MEDICAL_TOPICS for t in topics)

    jobs = [('openalex', lambda: openalex(query)), ('crossref', lambda: crossref(query)),
            ('semanticscholar', lambda: semantic_scholar(query))]
    if medical:
        jobs.insert(0, ('pubmed', lambda: pubmed(query, reviews=True)))
    results, failed = {}, []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {name: pool.submit(fn) for name, fn in jobs}
        for name, f in futures.items():
            try:
                results[name] = f.result()
            except Exception:
                results[name] = []
                failed.append(name)

    cited = guide.get('citedUrls') or []
    cited_dois = {d for d in (_doi(u) for u in cited) if d}
    merged, seen = [], set()
    order = [n for n, _ in jobs]
    longest = max((len(results[n]) for n in order), default=0)
    for i in range(longest):
        for n in order:
            if i >= len(results[n]):
                continue
            r = results[n][i]
            t = (r.get('title') or '').strip()
            k = r.get('doi') or t.lower()
            if not t or k in seen or t.lower() in seen or (r.get('doi') and r['doi'] in cited_dois):
                continue
            if n in ('openalex', 'crossref', 'semanticscholar') and not _relevant(r, query):
                continue
            seen.update({k, t.lower()})
            r['alreadyCited'] = False
            merged.append(r)
    merged = merged[:15]

    def add_citation(r):
        ident = r.get('doi') or (f"PMID:{r['pmid']}" if r.get('pmid') else None)
        if not ident:
            return r
        item = citoid(r['doi'] if r.get('doi') else r['pmid'])
        if item:
            r['cite'] = cite_template(item)
        return r

    with ThreadPoolExecutor(max_workers=5) as pool:
        merged = list(pool.map(add_citation, merged))

    res = {
        'title': title, 'wiki': dbname, 'query': query,
        'sourcesUsed': order, 'medical': medical, 'alreadyCitedSkipped': len(cited_dois),
        'results': merged, 'partial': bool(failed), 'failed': failed,
        'secs': round(time.time() - t0, 1),
    }
    _cache.set(key, res)
    return res
