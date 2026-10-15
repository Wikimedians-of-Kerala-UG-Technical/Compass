"""Personal stats: a reason to come back.

Edit streak, recent activity and how many readers saw the articles the editor worked on
in the last 30 days, from their live contributions (not the 6-hour profile cache).
"""
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

from services import wiki
from services.task_service import _pageviews

_cache = wiki.TTLCache(ttl=3600, maxsize=500, name='stats')
READER_ARTICLES = 25


def streaks(days, today=None):
    """(current, longest) runs of consecutive UTC days with an edit. A streak that
    ended yesterday still counts as current: today isn't over."""
    today = today or datetime.now(timezone.utc).date()
    days = sorted(set(days))
    longest, run, prev = 0, 0, None
    for d in days:
        run = run + 1 if prev and d - prev == timedelta(days=1) else 1
        longest = max(longest, run)
        prev = d
    current = 0
    if days and days[-1] >= today - timedelta(days=1):
        current, d = 0, days[-1]
        present = set(days)
        while d in present:
            current += 1
            d -= timedelta(days=1)
    return current, longest


def get_stats(username, dbname):
    username = wiki.normalize_username(username)
    return _cache.get_or_compute((username, dbname), lambda: _stats(username, dbname))


def _stats(username, dbname):
    t0 = time.time()
    since = (datetime.now(timezone.utc) - timedelta(days=90)).strftime('%Y-%m-%dT%H:%M:%SZ')
    contribs, cont = [], None
    while len(contribs) < 5000:
        params = {'action': 'query', 'list': 'usercontribs', 'ucuser': username, 'uclimit': 500,
                  'ucprop': 'title|timestamp|sizediff', 'ucend': since}
        if cont:
            params['uccontinue'] = cont
        data = wiki.api(dbname, params)
        contribs += (data.get('query') or {}).get('usercontribs') or []
        cont = (data.get('continue') or {}).get('uccontinue')
        if not cont:
            break

    days = [date.fromisoformat(c['timestamp'][:10]) for c in contribs]
    current, longest = streaks(days)
    month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
    recent = [c for c in contribs if c['timestamp'] >= month_ago]
    recent_articles = list(dict.fromkeys(c['title'] for c in recent if (c.get('ns') or 0) == 0))

    def views(title):
        try:
            return _pageviews(dbname, title)
        except Exception:
            return None
    with ThreadPoolExecutor(max_workers=6) as pool:
        per_day = list(pool.map(views, recent_articles[:READER_ARTICLES]))
    known = [v for v in per_day if v is not None]
    top = sorted(((t, v) for t, v in zip(recent_articles, per_day) if v), key=lambda tv: -tv[1])[:5]

    by_day = {}
    for d in days:
        by_day[d.isoformat()] = by_day.get(d.isoformat(), 0) + 1
    return {
        'username': username,
        'wiki': dbname,
        'streak': {'current': current, 'longest90': longest},
        'last30': {
            'edits': len(recent),
            'articles': len(recent_articles),
            'bytesAdded': sum(max(c.get('sizediff') or 0, 0) for c in recent),
        },
        'readers': {
            # Average daily views over 30 days, times 30, for the articles checked.
            'monthly': sum(known) * 30,
            'articlesChecked': len(known),
            'articlesTotal': len(recent_articles),
            'top': [{'title': t, 'perDay': v, 'url': wiki.page_url(dbname, t)} for t, v in top],
        },
        'calendar': by_day,  # 'YYYY-MM-DD' -> edits, last 90 days
        'secs': round(time.time() - t0, 1),
    }
