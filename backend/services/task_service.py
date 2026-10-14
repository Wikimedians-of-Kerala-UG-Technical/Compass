"""Task recommendations on the editor's home wiki.

Candidates come from precise CirrusSearch queries that pair a *scope* built from the
editor's own footprint with a *maintenance filter*:

  scope   articletopic:<their ML topic> articlecountry:<their country>
          incategory:"<a category they edit in>"
          nearcoord:<radius>,<lat>,<lon> of the place they edit most
          morelikethis:"<an article they edit a lot>"
  filter  incategory:"<tracking categories>" (or hastemplate: on wikis without them)
          hasrecommendation:link|image (Growth's machine-prepared tasks)

Every candidate is then read through `cirrusdoc` (one call per 50 articles) and ranked:

  score = 0.30 topic match + 0.20 place match + 0.15 impact + 0.15 feasibility
        + 0.10 freshness + 0.10 affinity
"""
import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from services import wiki, maintenance
from services.signals import article_signals, dated_tags, topic_label

PER_QUERY = 30
FINAL = 60
PAGEVIEW_TOP = 30
MAX_PER_SCOPE = 5
MAX_PER_TYPE = 15

AFFINITY = {
    'add_citations': ('references',), 'add_refs': ('references',), 'more_refs': ('references',),
    'inline_cites': ('references',), 'dead_links': ('references', 'minor'),
    'fix_orphan': ('linking',), 'add_link': ('linking', 'minor'), 'add_image': ('media',),
    'expand': ('major_add', 'creation', 'translation'), 'update': ('major_add', 'general'),
}
# Tracking-category issue names (as in dated categories) -> issue key, for tag age.
DATED_ISSUE = {
    'Articles with unsourced statements': 'add_citations',
    'Articles lacking sources': 'add_refs',
    'Articles needing additional references': 'more_refs',
    'Articles lacking in-text citations': 'inline_cites',
    'Orphaned articles': 'fix_orphan',
    'Articles with dead external links': 'dead_links',
    'Articles to be expanded': 'expand',
    'Wikipedia articles in need of updating': 'update',
}


def _haversine_km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a['lat'], a['lon'], b['lat'], b['lon']))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def _filters(dbname):
    """CirrusSearch filters that select articles needing work on this wiki."""
    local = maintenance.local_issues(dbname)
    keys = [k for k in maintenance.TASK_KEYS if k in local]
    cats = [local[k]['category'] for k in keys if maintenance.use_category(dbname, local[k])]
    tpls = [local[k]['template'] for k in keys
            if local[k]['template'] and not maintenance.use_category(dbname, local[k])]
    out = []
    if cats:
        out.append(('maintenance', 'incategory:"' + '|'.join(cats) + '"'))
    if tpls:
        out.append(('maintenance', 'hastemplate:"' + '|'.join(tpls) + '"'))
    out.append(('growth', 'hasrecommendation:link|image'))
    return out


def _scopes(profile, place=None):
    """(scope_id, search fragment, human reason) built from the editor's footprint."""
    scopes = []
    topics = profile.get('topics') or []
    countries = profile.get('countries') or []
    country = countries[0] if countries else None
    for i, t in enumerate(topics[:3]):
        if country:
            scopes.append((f'topic:{t["slug"]}+{country["a3"]}',
                           f'articletopic:{t["slug"]} articlecountry:{country["a3"]}',
                           f'{t["label"]} · {country["name"]} — a topic and country you edit a lot'))
        if not country or i == 0:
            scopes.append((f'topic:{t["slug"]}', f'articletopic:{t["slug"]}',
                           f'{t["label"]} — {round(t["share"] * 100)}% of the articles you edit'))
    if country and not topics:
        scopes.append((f'country:{country["a3"]}', f'articlecountry:{country["a3"]}',
                       f'{country["name"]} — where most of your articles are about'))
    cats = profile.get('topCategories') or []
    # Prefer categories with several of the editor's articles; 2 can be a coincidence.
    cats = ([c for c in cats if c['count'] >= 3] + [c for c in cats if c['count'] < 3])[:3]
    for c in cats:
        scopes.append((f'cat:{c["name"]}', f'incategory:"{c["name"]}"',
                       f'In “{c["name"]}”, where you edited {c["count"]} articles'))
    if place and place.get('coord'):
        lat, lon = place['coord']['lat'], place['coord']['lon']
        scopes.append(('near', f'nearcoord:25km,{lat:.4f},{lon:.4f}',
                       f'Within 25 km of {place["name"]}, where you edit'))
    for h in (profile.get('heavilyEdited') or [])[:2]:
        scopes.append((f'like:{h["title"]}', f'morelikethis:"{h["title"]}"',
                       f'Similar to {h["title"]}, which you edited {h["count"]} times'))
    return scopes


def _pageviews(dbname, title):
    end = datetime.now(timezone.utc).strftime('%Y%m%d')
    start = datetime.fromtimestamp(time.time() - 31 * 86400, timezone.utc).strftime('%Y%m%d')
    project = f'{wiki.lang(dbname)}.wikipedia'
    url = (f'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/all-access/user/'
           f'{wiki.quote_title(title).replace("/", "%2F")}/daily/{start}/{end}')
    data = wiki.get_json(url, retries=2, timeout=8)
    if data is None:
        raise RuntimeError('pageviews unavailable')  # rate-limited, or the API is down
    items = data.get('items') or []
    if not items:
        return 0
    return round(sum(i['views'] for i in items) / max(len(items), 1))


def _cosine(user_vec, article_vec):
    if not user_vec or not article_vec:
        return 0.0
    dot = sum(w * article_vec.get(k, 0) for k, w in user_vec.items())
    nu = math.sqrt(sum(w * w for w in user_vec.values()))
    na = math.sqrt(sum(w * w for w in article_vec.values()))
    return dot / (nu * na) if nu and na else 0.0


def _months_since(stamp):
    """'2022-04' -> months ago."""
    y, m = map(int, stamp.split('-'))
    now = datetime.now(timezone.utc)
    return (now.year - y) * 12 + now.month - m


def find_tasks(profile, place=None):
    dbname = profile['homeWiki']
    t0 = time.time()
    scopes = _scopes(profile, place)
    filters = _filters(dbname)
    # Growth's quick tasks only make sense with broad scopes; categories and similar
    # articles are already narrow enough that maintenance tags are the better signal.
    queries = [(sid, f'{frag} {flt}', reason, kind)
               for sid, frag, reason in scopes for kind, flt in filters
               if kind == 'maintenance' or sid.startswith(('topic:', 'country:', 'near'))]
    failed = []

    def run(q):
        sid, query, reason, kind = q
        try:
            results, _ = wiki.search(dbname, query, limit=PER_QUERY if kind == 'maintenance' else 10)
            return q, results
        except Exception as e:
            failed.append({'query': query, 'error': str(e)[:200]})
            return q, []

    candidates = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for (sid, query, reason, kind), results in pool.map(run, queries):
            for rank, r in enumerate(results):
                c = candidates.setdefault(r['title'], {'scopes': [], 'bestRank': rank})
                if sid not in [s[0] for s in c['scopes']]:
                    c['scopes'].append((sid, reason))
                c['bestRank'] = min(c['bestRank'], rank)

    edited = set(profile.get('_editedTitles') or [])
    titles = [t for t in candidates if t not in edited]
    sigs = article_signals(dbname, titles)

    user_vec = {t['path']: t['share'] for t in profile.get('topics') or []}
    user_vec.update({r['path']: r['share'] for r in profile.get('regions') or []})
    country_rank = {c['name']: i for i, c in enumerate(profile.get('countries') or [])}
    edit_types = profile.get('editTypes') or {}
    total_edits = sum(edit_types.values()) or 1
    newcomer = (profile.get('homeEdits') or 0) < 500

    scored = []
    for title in titles:
        sig = sigs.get(title)
        if not sig or sig.get('protected'):
            continue
        issues = maintenance.issues_of(dbname, sig)
        if not issues:
            continue
        if newcomer and ((sig.get('bytes') or 0) > 60000 or sig.get('quality') in ('GA', 'A', 'FA')):
            continue  # big or showcase articles are a poor first task
        dated = {DATED_ISSUE[k]: v for k, v in dated_tags(sig['categories']).items() if k in DATED_ISSUE}
        primary = max(issues, key=lambda k: maintenance.meta(k)['urgency'])
        m = maintenance.meta(primary)

        topic = _cosine(user_vec, sig['topics'])
        place_score = 0.0
        for name in sig['countries']:
            if name in country_rank:
                place_score = max(place_score, [1.0, .7, .5, .4][country_rank[name]])
        distance = None
        if place and place.get('coord') and sig.get('coord'):
            distance = _haversine_km(place['coord'], sig['coord'])
            if distance <= 50:
                place_score = 1.0
        # popularity_score is the article's share of the wiki's page views (from the search
        # index, so no extra call). Relative to its own wiki, which suits small wikis.
        popularity = sig.get('popularity') or 0
        impact = min(math.log10(1 + popularity * 1e8) / 3, 1)
        if sig.get('importance') in ('Top', 'High'):
            impact = min(impact + .3, 1)
        size = sig.get('bytes') or 0
        feasibility = 1.0 if size < 15000 else .7 if size < 40000 else .4 if size < 100000 else .1
        if sig.get('quality') in ('Stub', 'Start', 'C'):
            feasibility = min(feasibility + .15, 1)
        if sig.get('quality') in ('GA', 'FA', 'A'):
            feasibility *= .5
        if primary in ('add_link', 'add_image', 'add_citations', 'dead_links'):
            feasibility = min(feasibility + .1, 1)
        tag_date = dated.get(primary)
        freshness = .5
        if tag_date:
            months = _months_since(tag_date)
            freshness = 1.0 if months <= 12 else .7 if months <= 36 else .4 if months <= 96 else .2
        affinity = min(sum(edit_types.get(t, 0) for t in AFFINITY.get(primary, ())) / total_edits * 4, 1)
        if newcomer and primary in ('add_link', 'add_image'):
            affinity = 1.0

        score = (0.30 * topic + 0.20 * place_score + 0.15 * impact + 0.15 * feasibility
                 + 0.10 * freshness + 0.10 * affinity + 0.05 * m['urgency'])
        if any(sid.startswith(('cat:', 'like:', 'near')) for sid, _ in candidates[title]['scopes']):
            score += 0.05  # found through the editor's own categories, articles or place
        if primary in ('add_link', 'add_image') and not newcomer:
            score -= 0.05  # quick wins, but experienced editors get more out of real gaps

        best_topic = max(((k, w) for k, w in sig['topics'].items() if k in user_vec),
                         key=lambda kv: kv[1], default=(None, 0))[0]
        details = []
        if sig.get('quality'):
            details.append(f'{sig["quality"]}-class')
        details.append(f'{max(round(size / 1000), 1)} kB')
        if tag_date:
            details.append(f'tagged since {tag_date}')
        if distance is not None and distance <= 50:
            details.append(f'{round(distance)} km from {place["name"]}')
        scored.append({
            'title': title,
            'wiki': dbname,
            'url': wiki.page_url(dbname, title),
            'editUrl': wiki.edit_url(dbname, title),
            'type': primary,
            'issues': [{'key': k, 'label': maintenance.meta(k)['short'], 'since': dated.get(k)} for k in issues],
            'meta': {'label': m['label'], 'effort': m['effort'], 'min': m['minutes']},
            'topic': topic_label(best_topic) if best_topic else None,
            'country': next(iter(sig['countries']), None),
            'reason': candidates[title]['scopes'][0][1],
            'reasons': [r for _, r in candidates[title]['scopes'][:3]],
            'details': details,
            'quality': sig.get('quality'),
            'size': size,
            'scope': candidates[title]['scopes'][0][0],
            'signals': {
                'topic': round(topic, 3), 'place': round(place_score, 3), 'impact': round(impact, 3),
                'feasibility': round(feasibility, 3), 'freshness': round(freshness, 3), 'affinity': round(affinity, 3),
            },
            'score': round(score, 4),
            'pageviews': None,
            'staleDays': _days_since(sig.get('lastEdit')),
        })

    scored.sort(key=lambda t: t['score'], reverse=True)

    ranked = sorted(scored, key=lambda t: t['score'], reverse=True)

    # Diversify: no single scope or task type should take over the list.
    per_scope, per_type, head, tail = {}, {}, [], []
    for t in ranked:
        s, ty = t['scope'], t['type']
        if per_scope.get(s, 0) < MAX_PER_SCOPE and per_type.get(ty, 0) < MAX_PER_TYPE:
            head.append(t)
            per_scope[s] = per_scope.get(s, 0) + 1
            per_type[ty] = per_type.get(ty, 0) + 1
        else:
            tail.append(t)
    tasks = (head + tail)[:FINAL]

    # Real 30-day pageviews, shown on the cards (ranking already used popularity_score).
    pv_failed = []

    def views(task):
        try:
            return _pageviews(dbname, task['title'])
        except Exception:
            pv_failed.append(task['title'])
            return None

    shown = tasks[:PAGEVIEW_TOP]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for task, v in zip(shown, pool.map(views, shown)):
            task['pageviews'] = v
            if v:
                task['details'].append(f'{v:,} views/day')
    if pv_failed:
        failed.append({'query': 'pageviews', 'error': f'{len(pv_failed)} lookups rate-limited'})
    return {
        'wiki': dbname,
        'tasks': tasks,
        'scopes': [{'id': s, 'query': f, 'reason': r} for s, f, r in scopes],
        'candidates': len(titles),
        'partial': bool(failed),
        'failed': failed[:5],
        'secs': round(time.time() - t0, 1),
    }


def _days_since(ts):
    if not ts:
        return None
    try:
        dt = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - dt).days
