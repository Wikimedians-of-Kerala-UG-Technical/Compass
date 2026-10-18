"""Events: an Event Registration event's worklist, ranked for one participant.

Organisers run their edit-a-thon with Wikimedia's own Event Registration tool
(CampaignEvents): signup, the list of articles to work on (the *worklist*), and
contribution tracking with a goal bar. Compass doesn't duplicate any of that. It adds
the one thing the tool doesn't do: every participant sees the same worklist there, and
here each one sees it ordered by what suits them (their topics, their places, the kind
of edits they make, articles they already know).

- Event:      GET /w/rest.php/campaignevents/v0/event_registration/{id} (Meta; ids are global)
- Worklist:   the JSON page "<event page>/Worklist", e.g. {"enwiki": ["Title", ...]}
- Participants: GET .../event_registration/{id}/participants (public registrations only)
"""
import re
import time

from services import wiki, maintenance
from services.signals import article_signals, topic_label
from services.task_service import AFFINITY, _cosine

CENTRAL = 'https://meta.wikimedia.org/w/rest.php/campaignevents/v0'
MAX_RANKED = 1000       # worklist articles scored per request
SHOWN = 100
MAX_PARTICIPANTS = 200
WEIGHTS = {'topic': 0.45, 'place': 0.25, 'feasibility': 0.15, 'affinity': 0.15}
_events = wiki.TTLCache(ttl=10 * 60, maxsize=300, name='events')
_rankings = wiki.TTLCache(ttl=30 * 60, maxsize=500, name='event-rankings')

EVENT_ID_IN_URL = re.compile(r'EventDetails/(\d+)')
EVENT_ID_IN_HTML = re.compile(r'"wgCampaignEventsEventID":(\d+)')


def resolve(ref):
    """An event id from what an organiser would paste: '4579', a Special:EventDetails
    link, or the event page ('Event:Foo' or its URL, on any wiki)."""
    ref = (ref or '').strip()
    if ref.isdigit():
        return int(ref)
    m = EVENT_ID_IN_URL.search(ref)
    if m:
        return int(m.group(1))
    m = re.match(r'https?://([^/]+)/wiki/(.+)', ref)
    page_host, title = (m.group(1), m.group(2)) if m else ('meta.wikimedia.org', ref)
    if not title.replace('_', ' ').startswith('Event:') or not page_host.endswith(('.wikipedia.org', '.wikimedia.org')):
        raise wiki.UserError('Paste an event ID, its Special:EventDetails link or its Event: page.', 400)
    try:
        html = wiki.get_text(f'https://{page_host}/wiki/{wiki.quote_title(title.split("#")[0])}')
    except Exception:
        raise wiki.UserError(f'Could not open {title.replace("_", " ")}.') from None
    m = EVENT_ID_IN_HTML.search(html)
    if not m:
        raise wiki.UserError(f'{title.replace("_", " ")} has no Event Registration.')
    return int(m.group(1))


def get_event(event_id):
    return _events.get_or_compute(('event', event_id), lambda: _load_event(event_id))


def _load_event(event_id):
    e = wiki.get_json(f'{CENTRAL}/event_registration/{event_id}', retries=2)
    if not e or 'id' not in e:
        raise wiki.UserError(f'There is no event with ID {event_id}.')
    page_wiki = e.get('event_page_wiki') or 'metawiki'
    return {
        'id': e['id'],
        'name': e.get('name'),
        'status': e.get('status'),
        'starts': _iso(e.get('start_time')),
        'ends': _iso(e.get('end_time')),
        'timezone': e.get('timezone'),
        'wikis': e.get('wikis') or [],
        'topics': e.get('topics') or [],
        'goal': {'type': e['goal_type'], 'target': e.get('goal_target')} if e.get('goal_type') else None,
        'tracksContributions': bool(e.get('tracks_contributions')),
        'eventPage': e.get('event_page'),
        'eventPageUrl': wiki.page_url(page_wiki, e['event_page']) if e.get('event_page') else None,
        'detailsUrl': f'https://{wiki.host(page_wiki)}/wiki/Special:EventDetails/{e["id"]}',
        'worklist': _worklist(page_wiki, e.get('event_page')),
        'participants': _participants(event_id),
    }


def _iso(ts):
    """'20261017090000' -> '2026-10-17T09:00:00' (in the event's own time zone)."""
    if not ts or len(ts) != 14:
        return None
    return f'{ts[:4]}-{ts[4:6]}-{ts[6:8]}T{ts[8:10]}:{ts[10:12]}:{ts[12:]}'


def _worklist(page_wiki, event_page):
    """{dbname: [titles]}; empty when the event has no worklist yet."""
    if not event_page:
        return {}
    url = f'https://{wiki.host(page_wiki)}/w/index.php'
    data = wiki.get_json(url, params={'title': f'{event_page}/Worklist', 'action': 'raw'}, retries=2)
    if not isinstance(data, dict):
        return {}
    return {db: [t for t in titles if isinstance(t, str)] for db, titles in data.items()
            if isinstance(titles, list) and db.endswith('wiki')}


def _participants(event_id):
    """Public participants' usernames, oldest registration first."""
    names, last = [], None
    while len(names) < MAX_PARTICIPANTS:
        params = {'include_private': 'false'}
        if last:
            params['last_participant_id'] = last
        page = wiki.get_json(f'{CENTRAL}/event_registration/{event_id}/participants', params=params, retries=2)
        if not isinstance(page, list) or not page:
            break
        names += [p['user_name'] for p in page if p.get('user_name')]
        last = page[-1].get('participant_id')
        if not last or len(page) < 20:
            break
    return names[:MAX_PARTICIPANTS]


def rank_for(event_id, username, dbname=None):
    username = wiki.normalize_username(username)
    if not username:
        raise wiki.UserError('Please enter a username.', 400)
    event = get_event(event_id)
    worklist = event['worklist']
    if not worklist:
        raise wiki.UserError('This event has no worklist yet. Organisers add one on the event page.')
    if dbname and dbname not in worklist:
        raise wiki.UserError(f'The worklist has no articles on {dbname}.', 400)
    key = (event_id, username, dbname)
    return _rankings.get_or_compute(key, lambda: _rank(event, username, dbname))


def _profile_for(username, worklist):
    """The editor's profile on a worklist wiki they edit, else on their home wiki
    (topics and countries are the same everywhere, so it still ranks)."""
    from services.profile_service import build_profile
    profile = build_profile(username)
    if profile['homeWiki'] in worklist:
        return profile
    for w in sorted(worklist, key=lambda d: len(worklist[d]), reverse=True):
        try:
            return build_profile(username, w)
        except wiki.UserError:
            continue
    return profile


def _rank(event, username, dbname):
    t0 = time.time()
    worklist = event['worklist']
    profile = _profile_for(username, worklist)
    if not dbname:
        dbname = profile['homeWiki'] if profile['homeWiki'] in worklist else max(worklist, key=lambda d: len(worklist[d]))
    titles = worklist[dbname][:MAX_RANKED]
    sigs = article_signals(dbname, titles)
    edited = set(profile.get('_editedTitles') or []) if profile['homeWiki'] == dbname else set()

    items = [_score(dbname, title, sigs[title], profile, title in edited) for title in titles if title in sigs]
    items.sort(key=lambda i: i['score'], reverse=True)
    missing = [t for t in titles if t not in sigs]
    return {
        'event': {k: event[k] for k in ('id', 'name', 'starts', 'ends', 'detailsUrl', 'eventPageUrl')},
        'username': profile['username'],
        'wiki': dbname,
        'wikis': {w: len(ts) for w, ts in worklist.items()},
        'profileWiki': profile['homeWiki'],
        'items': items[:SHOWN],
        'toCreate': [{'title': t, 'url': wiki.page_url(dbname, t), 'editUrl': wiki.edit_url(dbname, t)}
                     for t in missing[:50]],
        'total': len(titles),
        'secs': round(time.time() - t0, 1),
    }


def _score(dbname, title, sig, profile, edited_before):
    user_vec = {t['path']: t['share'] for t in profile.get('topics') or []}
    user_vec.update({r['path']: r['share'] for r in profile.get('regions') or []})
    countries = profile.get('countries') or []
    country_rank = {c['name']: i for i, c in enumerate(countries)}
    edit_types = profile.get('editTypes') or {}
    total_edits = sum(edit_types.values()) or 1

    topic = _cosine(user_vec, sig['topics'])
    place, place_name = 0.0, None
    for name in sig['countries']:
        if name in country_rank and [1.0, .7, .5, .4][min(country_rank[name], 3)] > place:
            place, place_name = [1.0, .7, .5, .4][min(country_rank[name], 3)], name
    issues = maintenance.issues_of(dbname, sig)
    primary = max(issues, key=lambda k: maintenance.meta(k)['urgency']) if issues else None
    size = sig.get('bytes') or 0
    feasibility = 1.0 if size < 15000 else .7 if size < 40000 else .4 if size < 100000 else .1
    if sig.get('quality') in ('Stub', 'Start', 'C'):
        feasibility = min(feasibility + .15, 1)
    # With no tagged need, a short article mostly wants expanding.
    kinds = AFFINITY.get(primary, ()) if primary else AFFINITY['expand'] if size < 15000 else ('general',)
    affinity = min(sum(edit_types.get(t, 0) for t in kinds) / total_edits * 4, 1)

    signals = {'topic': topic, 'place': place, 'feasibility': feasibility, 'affinity': affinity}
    score = sum(WEIGHTS[k] * v for k, v in signals.items())
    if primary:
        score += 0.05 * maintenance.meta(primary)['urgency']
    if edited_before:
        score += 0.1

    reasons = []
    best_topic = max(((k, w) for k, w in sig['topics'].items() if k in user_vec), key=lambda kv: kv[1], default=(None, 0))[0]
    if best_topic and topic >= 0.2:
        reasons.append(f'{topic_label(best_topic)}, a topic you edit a lot')
    if place_name:
        reasons.append(f'About {place_name}, where many of your articles are')
    if edited_before:
        reasons.append("You've edited it before")
    if not reasons:
        reasons.append("On the event's worklist")

    details = [f'{sig["quality"]}-class'] if sig.get('quality') else []
    details.append(f'{max(round(size / 1000), 1)} kB')
    # Organisers often list short articles with no maintenance tag: the work is expanding them.
    m = maintenance.meta(primary or 'expand') if primary or size < 15000 else None
    return {
        'title': title,
        'wiki': dbname,
        'url': wiki.page_url(dbname, title),
        'editUrl': wiki.edit_url(dbname, title),
        'needs': [{'key': k, 'label': maintenance.meta(k)['short']} for k in issues],
        'meta': {'label': m['label'], 'min': m['minutes']} if m else None,
        'reasons': reasons,
        'details': details,
        'signals': {k: round(v, 3) for k, v in signals.items()},
        'score': round(score, 4),
    }
