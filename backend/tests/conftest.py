"""Tests run offline: caches are in memory and any real HTTP call fails."""
import os
import sys

os.environ['COMPASS_CACHE_PATH'] = ''
os.environ['COMPASS_RATE_LIMIT'] = '0'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest  # noqa: E402

from services import wiki  # noqa: E402


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError(f'unexpected network call: {args[:2]}')
    monkeypatch.setattr(wiki.session, 'request', refuse)
    monkeypatch.setattr(wiki.session, 'get', refuse)
    monkeypatch.setattr(wiki.session, 'post', refuse)


@pytest.fixture
def client():
    from app import create_app
    app = create_app()
    app.testing = True
    return app.test_client()
