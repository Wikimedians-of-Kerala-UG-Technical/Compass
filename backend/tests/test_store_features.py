import pytest

from services import feedback_service as fb, store, wiki
from services.alerts_service import AlertHub


def test_feedback_record_and_hide():
    fb.record('doc_James', 'enwiki', 'Malaria', 'up', signals={'topic': 0.8, 'bogus': 1, 'place': 'x'})
    fb.record('Doc James', 'enwiki', 'Gout', 'dismiss')
    fb.record('Doc James', 'enwiki', 'Malaria', 'done')
    latest = fb.latest('Doc_James', 'enwiki')
    assert latest['Malaria']['action'] == 'done' and latest['Malaria']['username'] == 'Doc James'
    assert fb.hidden_titles('Doc James', 'enwiki') == {'Malaria', 'Gout'}
    assert store.loads(store.row("SELECT signals FROM feedback WHERE action = 'up'")['signals']) == {'topic': 0.8}
    assert fb.training_rows() == [({'topic': 0.8, 'place': 0, 'impact': 0, 'feasibility': 0,
                                    'freshness': 0, 'affinity': 0}, 1)]


@pytest.mark.parametrize('kwargs', [
    {'action': 'love'}, {'title': ''}, {'title': 'x' * 300}, {'dbname': 'nonsense'},
])
def test_feedback_validation(kwargs):
    args = {'username': 'A', 'dbname': 'enwiki', 'title': 'T', 'action': 'up', **kwargs}
    with pytest.raises(wiki.UserError):
        fb.record(**args)


def test_verify_edits_marks_only_later_edits(monkeypatch):
    fb.record('A', 'enwiki', 'Edited later', 'up')
    fb.record('A', 'enwiki', 'Never edited', 'up')
    store.execute('UPDATE feedback SET created = ?', (1_790_000_000,))  # 2026-09-21
    monkeypatch.setattr(wiki, 'api', lambda dbname, params, **kw: {'query': {'usercontribs': [
        {'title': 'Edited later', 'timestamp': '2026-10-01T10:00:00Z'},
        {'title': 'Never edited', 'timestamp': '2026-09-01T10:00:00Z'},  # before the vote
    ]}})
    monkeypatch.setattr(fb.time, 'time', lambda: 1_791_000_000)
    assert fb.verify_edits('A', 'enwiki') == 1
    assert fb.summary('A', 'enwiki')['edited'] == 1


def test_alert_hub_routes_events(monkeypatch):
    hub = AlertHub(url='http://unused')
    monkeypatch.setattr(hub, '_tracking_categories', lambda dbname: {'All articles lacking sources': 'add_refs'})
    monkeypatch.setattr('threading.Thread.start', lambda self: None)  # no stream in tests
    sid, q = hub.subscribe('Me', 'mlwiki', ['കൊച്ചി'])
    hub.handle({'type': 'edit', 'namespace': 0, 'wiki': 'mlwiki', 'title': 'കൊച്ചി', 'user': 'Other',
                'revision': {'new': 7}, 'timestamp': 1})
    hub.handle({'type': 'edit', 'namespace': 0, 'wiki': 'mlwiki', 'title': 'കൊച്ചി', 'user': 'Me', 'timestamp': 2})
    hub.handle({'type': 'edit', 'namespace': 0, 'wiki': 'enwiki', 'title': 'കൊച്ചി', 'user': 'Other', 'timestamp': 3})
    monkeypatch.setattr(hub, '_has_category', lambda dbname, title, cat: True)
    hub.handle({'type': 'categorize', 'wiki': 'mlwiki', 'title': 'വർഗ്ഗം:All articles lacking sources',
                'comment': '[[:കൊച്ചി]] വർഗ്ഗത്തിൽ ചേർത്തു', 'user': 'Bot', 'timestamp': 4})
    alerts = [q.get_nowait() for _ in range(q.qsize())]
    assert [(a['kind'], a['user']) for a in alerts] == [('edit', 'Other'), ('tagged', 'Bot')]
    assert alerts[0]['diffUrl'] == 'https://ml.wikipedia.org/w/index.php?diff=7'
    hub.unsubscribe(sid)
    assert hub.subscribers() == 0 and hub._index == {}
