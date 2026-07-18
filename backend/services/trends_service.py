import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from services.http_client import session

WIKI = 'https://en.wikipedia.org/w/api.php'
PAGEVIEWS = 'https://wikimedia.org/api/rest_v1'

LI_RE = re.compile(r'<li[^>]*>([\s\S]*?)</li>', re.IGNORECASE)
TAG_RE = re.compile(r'<[^>]+>')
LINK_RE = re.compile(r'<a[^>]+title="([^"]+)"[^>]*>')


def wiki_get(params):
    params = dict(params, format='json')
    r = session.get(WIKI, params=params)
    r.raise_for_status()
    return r.json()


def _parse_list_items(html, source, limit):
    items = []
    for m in LI_RE.finditer(html):
        if len(items) >= limit:
            break
        li = m.group(1)
        text = TAG_RE.sub(' ', li)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) < 15:
            continue
        articles = []
        for lm in LINK_RE.finditer(li):
            title = lm.group(1)
            if ':' not in title and title not in articles:
                articles.append(title)
        if articles:
            items.append({'text': text[:200], 'articles': articles, 'source': source})
    return items


def parse_current_events_deep():
    try:
        d = wiki_get({'action': 'parse', 'page': 'Portal:Current_events', 'prop': 'text', 'section': 0})
        html = (d.get('parse') or {}).get('text', {}).get('*', '')
        return _parse_list_items(html, 'current_events', 25)
    except Exception:
        return []


def parse_recent_deaths():
    try:
        d = wiki_get({
            'action': 'query', 'list': 'categorymembers', 'cmtitle': 'Category:Recent_deaths',
            'cmlimit': 12, 'cmtype': 'page', 'cmnamespace': 0, 'cmsort': 'timestamp', 'cmdir': 'desc'
        })
        members = (d.get('query') or {}).get('categorymembers', [])
        return [{'text': f"{m['title']} — recently deceased", 'articles': [m['title']], 'source': 'recent_deaths'} for m in members]
    except Exception:
        return []


def parse_ongoing():
    try:
        d = wiki_get({
            'action': 'query', 'list': 'categorymembers', 'cmtitle': 'Category:Ongoing_events',
            'cmlimit': 12, 'cmtype': 'page', 'cmnamespace': 0
        })
        members = (d.get('query') or {}).get('categorymembers', [])
        return [{'text': f"{m['title']} — ongoing event", 'articles': [m['title']], 'source': 'ongoing'} for m in members]
    except Exception:
        return []


def parse_dyk():
    try:
        d = wiki_get({'action': 'parse', 'page': 'Template:Did_you_know', 'prop': 'text'})
        html = (d.get('parse') or {}).get('text', {}).get('*', '')
        return _parse_list_items(html, 'dyk', 10)
    except Exception:
        return []


def fetch_wiki_trending():
    try:
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        date_path = yesterday.strftime('%Y/%m/%d')
        r = session.get(f'{PAGEVIEWS}/metrics/pageviews/top/en.wikipedia/all-access/{date_path}', headers={'Accept': 'application/json'})
        if not r.ok:
            return []
        data = r.json()
        items = (data.get('items') or [{}])[0].get('articles', [])
        skip_prefixes = ('Special:', 'Wikipedia:', 'Portal:')
        filtered = [
            a for a in items
            if not a['article'].startswith(skip_prefixes)
            and a['article'] != 'Main_Page' and a['article'] != '-'
        ]
        return [
            {'title': a['article'].replace('_', ' '), 'views': a['views'], 'source': 'wiki_trending'}
            for a in filtered[:30]
        ]
    except Exception:
        return []


def get_trends():
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            'current_events': pool.submit(parse_current_events_deep),
            'recent_deaths': pool.submit(parse_recent_deaths),
            'ongoing': pool.submit(parse_ongoing),
            'dyk': pool.submit(parse_dyk),
            'wiki_trending': pool.submit(fetch_wiki_trending),
        }
        results = {k: f.result() for k, f in futures.items()}

    news = results['current_events'] + results['recent_deaths'] + results['ongoing'] + results['dyk']
    return {'news': news, 'trending': results['wiki_trending']}
