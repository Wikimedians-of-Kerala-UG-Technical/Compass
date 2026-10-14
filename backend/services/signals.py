"""Per-article signals from Wikipedia's own search index and assessments.

`prop=cirrusdoc` returns, for up to 50 articles per call and on every Wikipedia:
ML topic and country predictions (`weighted_tags`), Growth "add a link / image"
recommendations, popularity, incoming links, size, coordinates, categories
(including hidden tracking categories) and templates. PageAssessments adds the
WikiProject quality class where a wiki has it (enwiki and a few others).
"""
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

from services import wiki

_cache = wiki.TTLCache(ttl=24 * 3600, maxsize=20000, name='signals')

with open(os.path.join(os.path.dirname(__file__), '..', 'data', 'countries.json'), encoding='utf-8') as f:
    COUNTRIES = json.load(f)  # English country name -> {a2, a3, qid}

QUALITY_ORDER = ['Stub', 'Start', 'C', 'B', 'GA', 'A', 'FA']
MONTHS = {m: i for i, m in enumerate(
    ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
     'September', 'October', 'November', 'December'], 1)}
DATED_RE = re.compile(r'^(.*?) from ([A-Z][a-z]+) (\d{4})$')

CIRRUS_FIELDS = 'weighted_tags|popularity_score|incoming_links|text_bytes|coordinates|create_timestamp|timestamp|category|template'


def topic_slug(tag_path):
    """'Culture.Media.Films' -> 'films'; 'STEM.Medicine_&_Health' -> 'medicine-and-health'
    (the form CirrusSearch's `articletopic:` keyword accepts)."""
    last = tag_path.split('.')[-1].rstrip('*')
    return last.lower().replace('_&_', '-and-').replace('&', 'and').replace('_', '-').replace(' ', '-')


def topic_label(tag_path):
    return tag_path.split('.')[-1].rstrip('*').replace('_', ' ')


def is_region_topic(tag_path):
    return tag_path.startswith('Geography.Regions')


def country_info(name):
    c = COUNTRIES.get(name)
    return {'name': name, **c} if c else None


def _parse_doc(page):
    docs = page.get('cirrusdoc') or []
    if not docs:
        return None
    src = docs[0].get('source') or {}
    topics, countries, recs = {}, {}, set()
    pa_projects = []
    for tag in src.get('weighted_tags') or []:
        name, _, weight = tag.partition('|')
        weight = int(weight) / 1000 if weight.isdigit() else 1.0
        if name.startswith('classification.prediction.articletopic/'):
            topics[name.split('/', 1)[1]] = weight
        elif name.startswith('classification.prediction.articlecountry/'):
            countries[name.split('/', 1)[1]] = weight
        elif name.startswith('recommendation.'):
            recs.add(name.split('.', 1)[1].split('/')[0])
        elif name.startswith('ext.pageassessments.project/'):
            pa_projects.append(name.split('/', 1)[1])
    coords = [c['coord'] for c in src.get('coordinates') or [] if c.get('primary') and c.get('globe') == 'earth']
    return {
        'title': page.get('title'),
        'topics': topics,
        'countries': countries,
        'recommendations': sorted(recs),
        'projects': pa_projects,
        'popularity': src.get('popularity_score') or 0,
        'incomingLinks': src.get('incoming_links') or 0,
        'bytes': src.get('text_bytes') or 0,
        'coord': coords[0] if coords else None,
        'created': src.get('create_timestamp'),
        'lastEdit': src.get('timestamp'),
        'categories': src.get('category') or [],
        'templates': [t.split(':', 1)[-1] for t in src.get('template') or []],
    }


def article_signals(dbname, titles):
    """{title: signals} for the given titles on `dbname`. Missing pages are omitted."""
    out, need = {}, []
    for t in dict.fromkeys(titles):
        hit = _cache.get((dbname, t))
        if hit is not None:
            out[t] = hit
        else:
            need.append(t)
    if not need:
        return out
    batches = [need[i:i + 50] for i in range(0, len(need), 50)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for batch_out in pool.map(lambda b: _fetch_batch(dbname, b), batches):
            out.update(batch_out)
    return out


def _fetch_batch(dbname, batch):
    out, redirects = {}, {}
    params = {
        'action': 'query', 'titles': '|'.join(batch), 'redirects': 1,
        'prop': 'cirrusdoc|pageassessments|info', 'cdincludes': CIRRUS_FIELDS,
        'inprop': 'protection', 'palimit': 'max',
    }
    data = wiki.api(dbname, params, post=True)
    q = data.get('query') or {}
    for r in q.get('redirects') or []:
        redirects[r['to']] = r['from']
    for n in q.get('normalized') or []:
        redirects.setdefault(n['to'], n['from'])
    for page in q.get('pages') or []:
        if page.get('missing') is not None or page.get('ns', 0) != 0:
            continue
        sig = _parse_doc(page)
        if sig is None:
            continue
        assessments = page.get('pageassessments') or {}
        classes = [a.get('class') for a in assessments.values() if a.get('class') in QUALITY_ORDER]
        importances = [a.get('importance') for a in assessments.values() if a.get('importance')]
        sig['quality'] = max(classes, key=QUALITY_ORDER.index) if classes else None
        sig['importance'] = _best_importance(importances)
        sig['wikiprojects'] = [p for p in assessments if p != 'Project-independent assessment']
        sig['protected'] = any(p.get('type') == 'edit' and p.get('level') != 'autoconfirmed'
                               for p in page.get('protection') or [])
        sig['length'] = page.get('length') or sig['bytes']
        sig['lastRevid'] = page.get('lastrevid')
        sig['title'] = page['title']
        _cache.set((dbname, page['title']), sig)
        out[page['title']] = sig
        original = redirects.get(page['title'])
        if original:
            out[original] = sig
    return out


def _best_importance(values):
    order = ['Top', 'High', 'Mid', 'Low']
    found = [v for v in values if v in order]
    return min(found, key=order.index) if found else None


def dated_tags(categories):
    """Hidden dated tracking categories -> {issue: 'YYYY-MM'} (earliest date per issue).
    e.g. 'Articles needing additional references from April 2022'."""
    out = {}
    for c in categories:
        m = DATED_RE.match(c)
        if not m or m.group(2) not in MONTHS:
            continue
        stamp = f'{m.group(3)}-{MONTHS[m.group(2)]:02d}'
        issue = m.group(1)
        if issue not in out or stamp < out[issue]:
            out[issue] = stamp
    return out


def aggregate_profile(signals, weights=None):
    """Weighted sums of topic and country scores over a user's edited articles."""
    topics, countries = {}, {}
    for sig, k in zip(signals, weights or [1] * len(signals)):
        for t, w in sig['topics'].items():
            topics[t] = topics.get(t, 0) + w * k
        for c, w in sig['countries'].items():
            countries[c] = countries.get(c, 0) + w * k
    return topics, countries
