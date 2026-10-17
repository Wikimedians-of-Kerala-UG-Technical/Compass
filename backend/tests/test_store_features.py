import pytest

from services import feedback_service as fb, store, wiki


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
