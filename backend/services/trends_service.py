"""Trends: what readers are reading right now *that needs work*, near the editor.

- Readers in the editor's country (`pageviews/top-per-country/<ISO alpha-2>`), across
  the editor's Wikipedias.
- The editor's home wiki's most-read articles (`pageviews/top/<lang>.wikipedia`).
- Only articles that carry a maintenance tag or a Growth suggestion are kept, so every
  item is something a volunteer can improve while readers are looking.
- Traffic that looks automated (nearly all desktop, or nearly none) is dropped, the
  check the weekly Top 25 Report uses for bot spikes like *.xxx* topping India's list.
- Headlines from enwiki's Portal:Current events.
"""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from services import wiki, maintenance
from services.signals import article_signals

PAGEVIEWS = 'https://wikimedia.org/api/rest_v1/metrics/pageviews'
LI_RE = re.compile(r'<li[^>]*>([\s\S]*?)</li>', re.IGNORECASE)
TAG_RE = re.compile(r'<[^>]+>')
LINK_RE = re.compile(r'<a[^>]+title="([^"]+)"[^>]*>')
SKIP = re.compile(r'^(Main_Page|Special:|Wikipedia:|Portal:|File:|Help:|Talk:|User:|-$)')
_cache = wiki.TTLCache(ttl=3 * 3600, maxsize=200, name='trends')
# Human readers are 10–50% desktop depending on the country (India's top articles: 9–22%).
# A day that is >92% desktop, or <3% (*.xxx* in India in October 2026: 1.7%), is almost
# always a crawler or a script reloading one page.
DESKTOP_MAX, DESKTOP_MIN = 0.92, 0.03
ANOMALY_MIN_VIEWS = 1000


def _days():
    """Pageview dumps lag a day or two; try the most recent dates first."""
    today = datetime.now(timezone.utc)
    return [(today - timedelta(days=d)).strftime('%Y/%m/%d') for d in (1, 2, 3)]


def _main_namespace(dbname):
    """Main page titles differ per wiki; the Action API gives us the localized one."""
    return wiki.api(dbname, {'action': 'query', 'meta': 'siteinfo', 'siprop': 'general'})['query']['general']['mainpage']


def top_per_country(a2, projects, limit=40):
    for day in _days():
        data = wiki.get_json(f'{PAGEVIEWS}/top-per-country/{a2}/all-access/{day}', retries=1, timeout=20)
        items = ((data or {}).get('items') or [{}])[0].get('articles') or []
        if items:
            out = []
            for a in items:
                project = a.get('project', '')
                if project not in projects or SKIP.match(a['article']):
                    continue
                out.append({'title': a['article'].replace('_', ' '), 'views': a.get('views_ceil') or a.get('views'),
                            'wiki': project.replace('.wikipedia', '').replace('-', '_') + 'wiki', 'day': day})
                if len(out) >= limit:
                    break
            return out
    return []


def top_on_wiki(dbname, limit=40):
    project = f'{wiki.lang(dbname)}.wikipedia'
    try:
        main = _main_namespace(dbname).replace(' ', '_')
    except Exception:
        main = 'Main_Page'
    for day in _days():
        data = wiki.get_json(f'{PAGEVIEWS}/top/{project}/all-access/{day}', retries=1, timeout=20)
        items = ((data or {}).get('items') or [{}])[0].get('articles') or []
        if items:
            out = [{'title': a['article'].replace('_', ' '), 'views': a['views'], 'wiki': dbname, 'day': day}
                   for a in items if a['article'] != main and not SKIP.match(a['article']) and ':' not in a['article']]
            return out[:limit]
    return []


def _access_split(dbname, title, day):
    """(desktop views, all views) by human readers on one day, or None."""
    project = f'{wiki.lang(dbname)}.wikipedia'
    article = wiki.quote_title(title).replace('/', '%2F')
    out = []
    for access in ('desktop', 'all-access'):
        data = wiki.get_json(f'{PAGEVIEWS}/per-article/{project}/{access}/user/{article}/daily/'
                             f'{day.replace("/", "")}/{day.replace("/", "")}', retries=1, timeout=10)
        items = (data or {}).get('items') or []
        if not items:
            return None
        out.append(items[0].get('views') or 0)
    return tuple(out)


def looks_automated(desktop, total):
    if total < ANOMALY_MIN_VIEWS:
        return False
    share = desktop / total
    return share > DESKTOP_MAX or share < DESKTOP_MIN


def drop_anomalies(items):
    """Removes items whose traffic looks automated. Items that can't be checked stay."""
    def check(it):
        split = _access_split(it['wiki'], it['title'], it['day'])
        return split is not None and looks_automated(*split)
    with ThreadPoolExecutor(max_workers=6) as pool:
        flags = list(pool.map(check, items))
    return [it for it, bad in zip(items, flags) if not bad], sum(flags)


def _needing_work(items):
    """Keeps only articles with maintenance tags or Growth suggestions, annotated."""
    by_wiki = {}
    for it in items:
        by_wiki.setdefault(it['wiki'], []).append(it)
    out = []
    for dbname, its in by_wiki.items():
        try:
            sigs = article_signals(dbname, [i['title'] for i in its])
        except Exception:
            continue
        for it in its:
            sig = sigs.get(it['title'])
            if not sig:
                continue
            issues = maintenance.issues_of(dbname, sig)
            if not issues:
                continue
            out.append({
                **it,
                'url': wiki.page_url(dbname, it['title']),
                'editUrl': wiki.edit_url(dbname, it['title']),
                'issues': [{'key': k, 'label': maintenance.meta(k)['short']} for k in issues],
                'quality': sig.get('quality'),
            })
    return sorted(out, key=lambda i: -(i.get('views') or 0))


def current_events():
    try:
        d = wiki.api('enwiki', {'action': 'parse', 'page': 'Portal:Current_events', 'prop': 'text', 'section': 0})
        html = (d.get('parse') or {}).get('text', '')
    except Exception:
        return []
    items = []
    for m in LI_RE.finditer(html):
        li = m.group(1)
        if '<li' in li:  # a heading that wraps a nested list — its children are separate items
            continue
        text = re.sub(r'\s+', ' ', TAG_RE.sub(' ', li)).strip()
        if len(text) < 40:
            continue
        articles = list(dict.fromkeys(t for t in LINK_RE.findall(li) if ':' not in t))
        if articles:
            items.append({'text': text[:220], 'articles': articles[:4], 'source': 'current_events', 'wiki': 'enwiki'})
        if len(items) >= 12:
            break
    return items


def get_trends(country_a2=None, dbname='enwiki', languages=None):
    key = (country_a2, dbname, tuple(languages or []))
    return _cache.get_or_compute(key, lambda: _trends(country_a2, dbname, languages or []))


def _trends(country_a2, dbname, languages):
    projects = {f'{wiki.lang(dbname)}.wikipedia', 'en.wikipedia'} | {f'{l}.wikipedia' for l in languages}
    with ThreadPoolExecutor(max_workers=3) as pool:
        regional_f = pool.submit(top_per_country, country_a2, projects) if country_a2 else None
        home_f = pool.submit(top_on_wiki, dbname)
        news_f = pool.submit(current_events)
        regional = regional_f.result() if regional_f else []
        home = home_f.result()
        news = news_f.result()
    regional_work, regional_bots = drop_anomalies(_needing_work(regional))
    home_work, home_bots = drop_anomalies(_needing_work(home))
    # Alternate the two lists: the home wiki's numbers are much smaller than enwiki's,
    # so sorting by views alone would hide it.
    seen, trending = set(), []
    for i in range(max(len(regional_work), len(home_work))):
        for source, lst in (('wiki', home_work), ('country', regional_work)):
            if i < len(lst):
                it = lst[i]
                k = (it['wiki'], it['title'])
                if k not in seen:
                    seen.add(k)
                    trending.append({**it, 'source': source})
    return {
        'country': country_a2,
        'wiki': dbname,
        'trending': trending[:20],
        'checked': {'country': len(regional), 'wiki': len(home)},
        'droppedAsAutomated': regional_bots + home_bots,
        'news': news,
    }
