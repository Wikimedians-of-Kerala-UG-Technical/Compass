from services import trends_service as tr


def test_looks_automated():
    assert tr.looks_automated(1519, 87080)      # .xxx in India, 1.7% desktop
    assert tr.looks_automated(95000, 100000)    # a crawler
    assert not tr.looks_automated(7810, 72644)  # a real film release, 11% desktop
    assert not tr.looks_automated(10, 500)      # too few views to judge


def test_drop_anomalies_keeps_unchecked_items(monkeypatch):
    splits = {'.xxx': (1519, 87080), 'Jailer 2': (6058, 27689), 'Unknown': None}
    monkeypatch.setattr(tr, '_access_split', lambda dbname, title, day: splits[title])
    items = [{'title': t, 'wiki': 'enwiki', 'day': '2026/10/13'} for t in splits]
    kept, dropped = tr.drop_anomalies(items)
    assert [i['title'] for i in kept] == ['Jailer 2', 'Unknown'] and dropped == 1
