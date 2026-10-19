import pytest

from services import maintenance, task_service as ts

LOCAL = {k: {'template': v['template'], 'category': v['category'], 'categoryCount': 5000}
         for k, v in maintenance.ISSUES.items()}


def sig(title, **kw):
    base = {'title': title, 'topics': {'Culture.Media.Films': 0.9}, 'countries': {'India': 0.9},
            'recommendations': [], 'categories': [], 'templates': [], 'bytes': 8000, 'popularity': 1e-6,
            'quality': None, 'importance': None, 'protected': False, 'coord': None, 'lastEdit': None}
    return {**base, **kw}


PROFILE = {
    'homeWiki': 'enwiki', 'homeEdits': 5000, 'username': 'Tester',
    'topics': [{'path': 'Culture.Media.Films', 'slug': 'films', 'label': 'Films', 'share': 0.6}],
    'regions': [], 'countries': [{'name': 'India', 'a2': 'IN', 'a3': 'IND'}],
    'topCategories': [{'name': 'Malayalam films', 'count': 5}],
    'heavilyEdited': [{'title': 'Drishyam', 'count': 12}],
    'editTypes': {'references': 50, 'minor': 50}, '_editedTitles': ['Drishyam'],
}


@pytest.fixture
def wiki_stub(monkeypatch):
    queries = []
    articles = {
        'Unsourced film': sig('Unsourced film', categories=['All articles lacking sources',
                                                            'Articles lacking sources from March 2025']),
        'Link task': sig('Link task', recommendations=['link']),
        'Big FA': sig('Big FA', bytes=150000, quality='FA', categories=['All articles with unsourced statements']),
        'Drishyam': sig('Drishyam', categories=['All articles lacking sources']),
        'Protected': sig('Protected', protected=True, categories=['All articles lacking sources']),
    }

    def search(dbname, query, limit=10, sort=None, offset=0):
        queries.append(query)
        if 'hasrecommendation' in query:
            return [{'title': 'Link task'}], 1
        return [{'title': t} for t in ('Unsourced film', 'Big FA', 'Drishyam', 'Protected')], 4

    monkeypatch.setattr(maintenance, 'local_issues', lambda dbname: LOCAL)
    monkeypatch.setattr(ts.wiki, 'search', search)
    monkeypatch.setattr(ts, 'article_signals', lambda dbname, titles: {t: articles[t] for t in titles if t in articles})
    monkeypatch.setattr(ts, '_pageviews', lambda dbname, title: 42)
    return queries


def test_find_tasks_ranks_and_explains(wiki_stub):
    res = ts.find_tasks(PROFILE)
    titles = [t['title'] for t in res['tasks']]
    assert 'Drishyam' not in titles  # already edited by the user
    assert 'Protected' not in titles
    assert titles[0] == 'Unsourced film'
    top = res['tasks'][0]
    assert top['type'] == 'add_refs'
    assert top['issues'][0]['since'] == '2025-03'
    assert top['pageviews'] == 42 and '42 views/day' in top['details']
    assert set(top['signals']) == set(ts.WEIGHTS)
    assert res['mode'] == 'standard' and not res['partial']


def test_guided_mode_for_newcomers_only_uses_growth_tasks(wiki_stub):
    res = ts.find_tasks({**PROFILE, 'homeEdits': 50})
    assert res['mode'] == 'guided'
    assert all('hasrecommendation' in q for q in wiki_stub)
    assert 'hasrecommendation:link|image' in wiki_stub  # the whole-wiki fallback scope
    assert [t['title'] for t in res['tasks']] == ['Link task']
    assert all(i['key'] in maintenance.RECOMMENDATIONS for t in res['tasks'] for i in t['issues'])


def test_newcomers_skip_big_and_showcase_articles(wiki_stub):
    res = ts.find_tasks({**PROFILE, 'homeEdits': 300})
    assert 'Big FA' not in [t['title'] for t in res['tasks']]


def test_cosine_and_distance():
    assert ts._cosine({'a': 1}, {'a': 1}) == pytest.approx(1)
    assert ts._cosine({'a': 1}, {'b': 1}) == 0
    assert ts._cosine({}, {'a': 1}) == 0
    kochi, tvm = {'lat': 9.93, 'lon': 76.27}, {'lat': 8.52, 'lon': 76.94}
    assert 170 < ts._haversine_km(kochi, tvm) < 180


def test_scopes_include_place_and_similar_articles():
    scopes = ts._scopes(PROFILE, {'name': 'Kochi', 'coord': {'lat': 9.93, 'lon': 76.27}})
    ids = [s[0] for s in scopes]
    assert 'topic:films+IND' in ids and 'near' in ids and 'like:Drishyam' in ids and 'cat:Malayalam films' in ids
