import threading
import time

import pytest

from services import wiki


@pytest.mark.parametrize('dbname, host', [
    ('mlwiki', 'ml.wikipedia.org'),
    ('zh_min_nanwiki', 'zh-min-nan.wikipedia.org'),
    ('wikidatawiki', 'www.wikidata.org'),
    ('commonswiki', 'commons.wikimedia.org'),
])
def test_host(dbname, host):
    assert wiki.host(dbname) == host


def test_host_rejects_unknown_wiki():
    with pytest.raises(wiki.UserError):
        wiki.host('nonsense')


def test_lang_and_dbname_from_url():
    assert wiki.lang('zh_min_nanwiki') == 'zh-min-nan'
    assert wiki.dbname_from_url('https://zh-min-nan.wikipedia.org') == 'zh_min_nanwiki'
    assert wiki.dbname_from_url('https://www.wikidata.org') is None


def test_is_content_wikipedia():
    assert wiki.is_content_wikipedia('mlwiki')
    assert not wiki.is_content_wikipedia('wikidatawiki')
    assert not wiki.is_content_wikipedia('test2wiki')


@pytest.mark.parametrize('raw, normal', [
    ('vivek_joseph', 'Vivek joseph'),
    ('  Netha   Hussain ', 'Netha Hussain'),
    ('Doc_James', 'Doc James'),
    ('ranjithsiji', 'Ranjithsiji'),
    ('', ''),
])
def test_normalize_username(raw, normal):
    assert wiki.normalize_username(raw) == normal


def test_quote_title_keeps_readable_characters():
    assert wiki.quote_title('Kerala (state)') == 'Kerala_(state)'
    assert wiki.page_url('mlwiki', 'നെടുമുടി വേണു').startswith('https://ml.wikipedia.org/wiki/%E0')


@pytest.mark.parametrize('value', [
    {'a': (1, 2), 'b': {3, 4}, 'c': [None, True, 1.5, 'x']},
    {('enwiki', 'Title'): {'nested': (1, {'k': 'v'})}},
    {1: 'int key', '__t': 'looks like a tag'},
    ('tuple', ['in', ('a', 'list')]),
])
def test_encode_decode_round_trip(value):
    import json
    assert wiki._decode(json.loads(json.dumps(wiki._encode(value)))) == value


def test_encode_rejects_objects():
    with pytest.raises(TypeError):
        wiki._encode(object())


def test_ttl_cache_expires_and_evicts():
    c = wiki.TTLCache(ttl=60, maxsize=2)
    c.set('a', 1)
    c.set('b', 2)
    c.set('c', 3)  # evicts the oldest
    assert c.get('a') is None and c.get('b') == 2 and c.get('c') == 3
    c.set('b', 20)  # re-setting moves it to the back
    c.set('d', 4)
    assert c.get('c') is None and c.get('b') == 20
    short = wiki.TTLCache(ttl=-1)
    short.set('x', 1)
    assert short.get('x') is None


def test_get_or_compute_runs_once_and_drops_key_locks():
    c = wiki.TTLCache(ttl=60)
    calls = []

    def slow():
        calls.append(1)
        time.sleep(0.05)
        return 'v'
    threads = [threading.Thread(target=lambda: c.get_or_compute('k', slow)) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert calls == [1]
    assert c._key_locks == {}


def test_get_or_compute_releases_lock_on_error():
    c = wiki.TTLCache(ttl=60)
    with pytest.raises(RuntimeError):
        c.get_or_compute('k', lambda: (_ for _ in ()).throw(RuntimeError('boom')))
    assert c._key_locks == {}
    assert c.get_or_compute('k', lambda: 5) == 5


def test_disk_cache_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(wiki, 'CACHE_PATH', str(tmp_path / 'c.sqlite3'))
    monkeypatch.setattr(wiki, '_db_local', threading.local())
    a = wiki.TTLCache(ttl=60, name='t')
    a.set(('enwiki', 'X'), {'topics': {'A': 0.5}, 'coord': (1.0, 2.0)})
    b = wiki.TTLCache(ttl=60, name='t')  # a fresh process would see the same file
    assert b.get(('enwiki', 'X')) == {'topics': {'A': 0.5}, 'coord': (1.0, 2.0)}
