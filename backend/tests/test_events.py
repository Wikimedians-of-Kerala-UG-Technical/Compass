import pytest

from services import event_service as es, maintenance, wiki
from tests.test_tasks import LOCAL, PROFILE, sig

EVENT = {
    'id': 4579, 'name': 'Learn to Edit Wikipedia - Ho Workshop', 'event_page': 'Event:Ho Workshop',
    'event_page_wiki': 'metawiki', 'status': 'open', 'start_time': '20261017090000',
    'end_time': '20261017180000', 'timezone': 'Africa/Accra', 'wikis': ['enwiki'], 'topics': ['africa'],
    'tracks_contributions': True, 'goal_type': 'total_articles_edited', 'goal_target': 5,
}


@pytest.fixture(autouse=True)
def empty_caches():
    es._events._data.clear()
    es._rankings._data.clear()


@pytest.fixture
def central(monkeypatch):
    """The CampaignEvents API and the worklist page, served from memory."""
    calls = []

    def get_json(url, params=None, retries=3, timeout=30):
        calls.append((url, params))
        if url.endswith('/event_registration/4579'):
            return EVENT
        if url.endswith('/participants'):
            if (params or {}).get('last_participant_id'):
                return []
            return [{'participant_id': i, 'user_name': f'User {i}'} for i in range(20)]
        if url.endswith('/index.php') and params['title'] == 'Event:Ho Workshop/Worklist':
            return {'enwiki': ['Unsourced film', 'Kerala stub', 'Not yet written', 'Drishyam'],
                    'mlwiki': ['കൊച്ചി']}
        return None

    monkeypatch.setattr(wiki, 'get_json', get_json)
    return calls


@pytest.fixture
def ranking(central, monkeypatch):
    articles = {
        'Unsourced film': sig('Unsourced film', categories=['All articles lacking sources']),
        'Kerala stub': sig('Kerala stub', topics={'STEM.Biology': 0.9}, countries={}, quality='Stub'),
        'Drishyam': sig('Drishyam'),
    }
    monkeypatch.setattr(maintenance, 'local_issues', lambda dbname: LOCAL)
    monkeypatch.setattr(es, 'article_signals', lambda dbname, titles: {t: articles[t] for t in titles if t in articles})
    import services.profile_service as ps
    monkeypatch.setattr(ps, 'build_profile', lambda username, dbname=None: PROFILE)


@pytest.mark.parametrize('ref', ['4579', ' 4579 ', 'https://meta.wikimedia.org/wiki/Special:EventDetails/4579',
                                 'https://es.wikipedia.org/wiki/Especial:EventDetails/4579?tab=Worklist'])
def test_resolve_ids_and_links(ref):
    assert es.resolve(ref) == 4579


def test_resolve_event_page_reads_the_id_from_the_page(monkeypatch):
    seen = []
    monkeypatch.setattr(wiki, 'get_text', lambda url, timeout=30: seen.append(url) or '"wgCampaignEventsEventID":4579,')
    assert es.resolve('https://meta.wikimedia.org/wiki/Event:Ho_Workshop') == 4579
    assert es.resolve('Event:Ho Workshop') == 4579
    assert seen[1] == 'https://meta.wikimedia.org/wiki/Event:Ho_Workshop'


@pytest.mark.parametrize('ref', ['', 'Kerala', 'https://evil.example/wiki/Event:X'])
def test_resolve_rejects_other_input(ref):
    with pytest.raises(wiki.UserError):
        es.resolve(ref)


def test_get_event_reads_worklist_and_participants(central):
    e = es.get_event(4579)
    assert e['starts'] == '2026-10-17T09:00:00' and e['goal'] == {'type': 'total_articles_edited', 'target': 5}
    assert e['detailsUrl'] == 'https://meta.wikimedia.org/wiki/Special:EventDetails/4579'
    assert e['worklist']['enwiki'][0] == 'Unsourced film' and set(e['worklist']) == {'enwiki', 'mlwiki'}
    assert len(e['participants']) == 20
    assert any(p and p.get('last_participant_id') == 19 for _, p in central)  # paged on


def test_rank_orders_by_fit_and_lists_pages_to_create(ranking):
    r = es.rank_for(4579, 'Tester')
    titles = [i['title'] for i in r['items']]
    assert r['wiki'] == 'enwiki' and r['total'] == 4
    # On topic with a need that matches their edits (citations), then on topic and
    # already known to them, then off topic.
    assert titles == ['Unsourced film', 'Drishyam', 'Kerala stub']
    film, known, off = r['items']
    assert [n['key'] for n in film['needs']] == ['add_refs'] and film['meta']['min']
    assert "You've edited it before" in known['reasons'] and 'Films, a topic you edit a lot' in known['reasons']
    assert off['reasons'] == ["On the event's worklist"] and off['score'] < known['score']
    assert r['toCreate'] == [{'title': 'Not yet written', 'url': 'https://en.wikipedia.org/wiki/Not_yet_written',
                              'editUrl': wiki.edit_url('enwiki', 'Not yet written')}]


def test_rank_other_wiki_and_errors(ranking, monkeypatch):
    with pytest.raises(wiki.UserError):
        es.rank_for(4579, 'Tester', 'dewiki')
    monkeypatch.setitem(EVENT, 'event_page', 'Event:No worklist')
    es._events._data.clear()
    with pytest.raises(wiki.UserError):
        es.rank_for(4579, 'Someone else')


def test_routes(client, ranking):
    assert client.get('/api/events/resolve?ref=4579').get_json() == {'id': 4579}
    assert client.get('/api/events/4579').get_json()['name'] == EVENT['name']
    assert client.get('/api/events/4579/rank/Tester').get_json()['items']
    assert client.get('/api/events/resolve?ref=nope').status_code == 400


def test_worklist_index_reads_only_real_worklists(monkeypatch):
    es._worklist_index._data.clear()

    def api(dbname, params, **kw):
        assert params['srnamespace'] == es.EVENT_NS
        return {'query': {'search': [{'title': 'Event:Ho Workshop/Worklist'}, {'title': 'Event:Notes/Worklist'},
                                     {'title': 'Event:Sandbox/Worklist demo'}]}}

    def pages(dbname, titles, params, batch=50):
        assert titles == ['Event:Ho Workshop/Worklist', 'Event:Notes/Worklist']
        yield {'title': titles[0], 'revisions': [{'slots': {'main': {
            'contentmodel': 'worklist', 'content': '{"enwiki": ["Panafest", "Gbawe"], "mlwiki": ["കൊച്ചി"]}'}}}]}
        yield {'title': titles[1], 'revisions': [{'slots': {'main': {'contentmodel': 'wikitext', 'content': '== x =='}}}]}

    monkeypatch.setattr(wiki, 'api', api)
    monkeypatch.setattr(wiki, 'api_pages', pages)
    assert es.worklist_index() == {'enwiki': {'Panafest': ['Event:Ho Workshop'], 'Gbawe': ['Event:Ho Workshop']},
                                   'mlwiki': {'കൊച്ചി': ['Event:Ho Workshop']}}


def test_events_with_articles_keeps_events_that_have_not_ended(monkeypatch):
    monkeypatch.setattr(es, 'worklist_index', lambda: {'enwiki': {
        'Panafest': ['Event:Ho Workshop', 'Event:Old Drive'], 'Gbawe': ['Event:Ho Workshop'], 'Other': ['Event:Test']}})
    summaries = {
        'Event:Ho Workshop': {'id': 1, 'name': 'Ho', 'starts': '2099-01-01T09:00:00', 'ends': '2099-01-02T18:00:00', 'url': 'u1'},
        'Event:Old Drive': {'id': 2, 'name': 'Old', 'starts': '2020-01-01T09:00:00', 'ends': '2020-01-31T18:00:00', 'url': 'u2'},
        'Event:Test': None,  # a test event, or a page without registration
    }
    monkeypatch.setattr(es, '_event_summary', summaries.get)
    found = es.events_with_articles('enwiki', ['Gbawe', 'Panafest', 'Other', 'Unlisted'])
    assert found == [{**summaries['Event:Ho Workshop'], 'yourArticles': ['Gbawe', 'Panafest']}]
    assert es.events_with_articles('mlwiki', ['Panafest']) == []
