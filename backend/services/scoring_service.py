import time
from concurrent.futures import ThreadPoolExecutor

from services.http_client import session
from services.trends_service import wiki_get

PAGEVIEWS = 'https://wikimedia.org/api/rest_v1'

TASK_META = {
    'add_refs':      {'label': 'Add References', 'effort': 'med', 'min': 20},
    'fix_orphan':    {'label': 'Fix Orphan', 'effort': 'low', 'min': 5},
    'add_citations': {'label': 'Add Citations', 'effort': 'low', 'min': 10},
    'watchlist':     {'label': 'Your Watchlist', 'effort': 'med', 'min': 15},
    'followup':      {'label': 'Your Article', 'effort': 'med', 'min': 20},
}

URGENCY = {
    'add_refs': .75,
    'fix_orphan': .38,
    'add_citations': .65,
    'watchlist': .66,
    'followup': .68,
}

# task type -> profile edit-type keys that indicate the user has relevant experience
AFFINITY = {
    'add_refs': ('references',),
    'add_citations': ('references',),
    'fix_orphan': ('linking', 'wikilinks'),
    'watchlist': ('general', 'references'),
    'followup': ('creation', 'major_add'),
}

# 'personal' tasks (watchlist / followup) are about specific articles the user has a direct
# history with — they're relevant by construction, independent of the profile's topic ranking.
PERSONAL_TOPIC_WEIGHT = 0.9


def get_pageviews(title):
    try:
        end = time.strftime('%Y%m%d', time.gmtime(time.time() - 86400))
        start = time.strftime('%Y%m%d', time.gmtime(time.time() - 30 * 86400))
        path = title.replace(' ', '_')
        url = f'{PAGEVIEWS}/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{path}/daily/{start}/{end}'
        r = session.get(url, headers={'Accept': 'application/json'})
        if not r.ok:
            return {'avg': 0, 'trend': 0}
        items = r.json().get('items', [])
        if not items:
            return {'avg': 0, 'trend': 0}
        views = [i['views'] for i in items]
        avg = round(sum(views) / len(views))
        recent7 = sum(views[-7:])
        prior7 = sum(views[-14:-7]) if len(views) >= 14 else 0
        trend = round((recent7 - prior7) / prior7 * 100) if prior7 > 0 else 0
        return {'avg': avg, 'trend': trend}
    except Exception:
        return {'avg': 0, 'trend': 0}


def get_staleness_batch(titles):
    """title -> days since last touched. One batched prop=info call (MediaWiki caps at 50 titles)."""
    if not titles:
        return {}
    try:
        data = wiki_get({'action': 'query', 'titles': '|'.join(titles[:50]), 'prop': 'info'})
        pages = (data.get('query') or {}).get('pages') or {}
        now = time.time()
        result = {}
        for pg in pages.values():
            title = pg.get('title')
            touched = pg.get('touched')
            if not title or not touched:
                continue
            touched_ts = time.mktime(time.strptime(touched, '%Y-%m-%dT%H:%M:%SZ'))
            result[title] = max(0, round((now - touched_ts) / 86400))
        return result
    except Exception:
        return {}


def score_and_rank(tasks, top_topics=None, top_edit_types=None, geo=None, pageview_sample=16, max_per_type=12):
    """
    Composite score = topic match + type urgency + recent pageviews + affinity with the
    user's editing history + a small bonus for quick (low-effort) tasks + staleness (how
    long since the article was last touched) + a geo-focus bonus for geography tasks.
    Enriches only the top `pageview_sample` candidates with real pageview/staleness data
    (bounded API calls) to bound latency, then diversifies the final ranking so one task
    type can't dominate.
    """
    top_topics = top_topics or []
    edit_type_set = set(top_edit_types or [])
    topic_weight = {t: max(1 - i * 0.25, 0.15) for i, t in enumerate(top_topics)}

    def topic_score(topic):
        if topic == 'personal':
            return PERSONAL_TOPIC_WEIGHT
        return topic_weight.get(topic, 0.2)

    # Pre-rank by topic + urgency alone to pick which titles are worth a pageview/staleness lookup.
    prelim = sorted(
        tasks,
        key=lambda t: topic_score(t.get('topic')) + URGENCY.get(t.get('type'), 0.5),
        reverse=True,
    )
    sample_titles = [t['title'] for t in prelim[:pageview_sample]]
    pv_data = {}
    if sample_titles:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for title, pv in zip(sample_titles, pool.map(get_pageviews, sample_titles)):
                pv_data[title] = pv
    stale_data = get_staleness_batch(sample_titles)

    scored = []
    for t in tasks:
        ttype = t.get('type')
        meta = TASK_META.get(ttype, {'label': ttype, 'effort': 'med', 'min': 20})
        urgency = URGENCY.get(ttype, 0.5)
        tw = topic_score(t.get('topic'))
        pv = pv_data.get(t['title'], {'avg': 0, 'trend': 0})
        pv_score = min(pv['avg'] / 500, 1)
        affinity = 0.1 if edit_type_set & set(AFFINITY.get(ttype, ())) else 0
        effort_bonus = 0.1 if (meta['effort'] == 'low' or t.get('isQuick')) else 0
        trend_bonus = 0.05 if pv['trend'] > 30 else 0
        stale_days = stale_data.get(t['title'])
        stale_score = min(stale_days / 365, 1) if stale_days else 0
        geo_bonus = 0.06 if geo and t.get('topic') == 'geography' else 0

        composite = round(
            0.35 * tw + 0.25 * urgency + 0.15 * pv_score + 0.1 * effort_bonus + 0.1 * affinity
            + 0.1 * stale_score + trend_bonus + geo_bonus,
            3,
        )
        scored.append({
            **t,
            'meta': meta,
            'score': composite,
            'pageviews': pv['avg'],
            'trend': pv['trend'],
            'staleDays': stale_days or 0,
        })

    scored.sort(key=lambda t: t['score'], reverse=True)

    # Diversify: cap how many of one type can occupy the top of the list, without dropping
    # any tasks — overflow is appended after, still in score order.
    counts = {}
    head, tail = [], []
    for t in scored:
        c = counts.get(t['type'], 0)
        if c < max_per_type:
            head.append(t)
            counts[t['type']] = c + 1
        else:
            tail.append(t)
    return head + tail
