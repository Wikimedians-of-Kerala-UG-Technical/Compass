import routes.profile
import routes.tasks
from services import feedback_service, wiki


def test_health(client):
    assert client.get('/api/health').get_json() == {'ok': True}


def test_user_errors_keep_their_message(client, monkeypatch):
    def missing(username, dbname=None):
        raise wiki.UserError(f'No Wikimedia account named "{username}".')
    monkeypatch.setattr(routes.profile, 'build_profile', missing)
    r = client.get('/api/profile/Nobody')
    assert r.status_code == 404 and r.get_json() == {'error': 'No Wikimedia account named "Nobody".'}


def test_internal_errors_are_hidden(client, monkeypatch):
    def broken(username, dbname=None):
        raise RuntimeError('Request to https://internal.example/secret failed')
    monkeypatch.setattr(routes.profile, 'build_profile', broken)
    r = client.get('/api/profile/Someone')
    body = r.get_json()
    assert r.status_code == 500 and 'internal.example' not in body['error'] and body['errorId'] in body['error']


def test_unknown_route_is_json(client):
    r = client.get('/api/nope')
    assert r.status_code == 404 and 'error' in r.get_json()


def test_feedback_hides_tasks(client, monkeypatch):
    monkeypatch.setattr(routes.tasks, 'build_profile', lambda u, d=None: {'username': 'Tester', 'homeWiki': 'enwiki'})
    monkeypatch.setattr(routes.tasks, 'find_tasks', lambda p, place=None: {'tasks': [{'title': 'A'}, {'title': 'B'}]})
    assert client.post('/api/feedback', json={'username': 'Tester', 'wiki': 'enwiki', 'title': 'A',
                                              'action': 'dismiss'}).status_code == 201
    assert client.post('/api/feedback', json={'username': 'Tester', 'title': 'A', 'action': '??'}).status_code == 400
    body = client.get('/api/tasks/Tester').get_json()
    assert [t['title'] for t in body['tasks']] == ['B'] and body['hidden'] == 1
    assert feedback_service.hidden_titles('Tester', 'enwiki') == {'A'}
    assert body['hiddenTasks'] == [{'title': 'A'}]  # returned so the editor can restore it
    # Undo: the vote goes and the task comes back.
    r = client.delete('/api/feedback/Tester?wiki=enwiki&title=A')
    assert r.status_code == 200 and r.get_json() == {'title': 'A', 'cleared': 1}
    body = client.get('/api/tasks/Tester').get_json()
    assert [t['title'] for t in body['tasks']] == ['A', 'B'] and 'hiddenTasks' not in body
    assert client.delete('/api/feedback/Tester?wiki=enwiki').status_code == 400


def test_rate_limit(monkeypatch):
    monkeypatch.setenv('COMPASS_RATE_LIMIT', '2/minute')
    from app import create_app
    c = create_app().test_client()
    codes = [c.get('/api/health').status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_cors_default_allows_dev_server_only(client):
    ok = client.get('/api/health', headers={'Origin': 'http://localhost:5173'})
    bad = client.get('/api/health', headers={'Origin': 'https://evil.example'})
    assert ok.headers.get('Access-Control-Allow-Origin') == 'http://localhost:5173'
    assert 'Access-Control-Allow-Origin' not in bad.headers


def test_frontend_fallback(tmp_path, monkeypatch):
    (tmp_path / 'index.html').write_text('<div id="app"></div>')
    (tmp_path / 'app.js').write_text('1')
    monkeypatch.setenv('COMPASS_STATIC_DIR', str(tmp_path))
    from app import create_app
    c = create_app().test_client()
    assert c.get('/u/Ranjithsiji/tasks').data == b'<div id="app"></div>'
    assert c.get('/app.js').data == b'1'
    assert c.get('/api/nothing').status_code == 404
