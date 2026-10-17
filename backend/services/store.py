"""Compass's own data: task feedback.

Unlike the caches in wiki.py, nothing here can be fetched again from Wikimedia, so it
lives in its own SQLite file (COMPASS_DB_PATH) that is safe to back up and never purged.
"""
import json
import os
import sqlite3
import threading

DB_PATH = os.environ.get('COMPASS_DB_PATH', os.path.join(os.path.dirname(__file__), '..', '.data', 'compass.db'))
_local = threading.local()

SCHEMA = '''
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    wiki TEXT NOT NULL,
    title TEXT NOT NULL,
    task_type TEXT,
    action TEXT NOT NULL,          -- up | down | done | dismiss
    scope TEXT,
    signals TEXT,                  -- JSON: the ranking signals the task was shown with
    score REAL,
    created REAL NOT NULL,
    edited_at TEXT                 -- set once the editor's edit on the article is seen
);
CREATE INDEX IF NOT EXISTS feedback_user ON feedback (username, wiki, created);
'''


def db():
    conn = getattr(_local, 'conn', None)
    if conn is None:
        if DB_PATH != ':memory:':
            os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        conn.executescript(SCHEMA)
        _local.conn = conn
    return conn


def rows(sql, params=()):
    return [dict(r) for r in db().execute(sql, params).fetchall()]


def row(sql, params=()):
    r = db().execute(sql, params).fetchone()
    return dict(r) if r else None


def execute(sql, params=()):
    conn = db()
    cur = conn.execute(sql, params)
    conn.commit()
    return cur


def dumps(value):
    return json.dumps(value, ensure_ascii=False) if value is not None else None


def loads(text):
    return json.loads(text) if text else None


def reset_for_tests(path=':memory:'):
    """Points the store at a fresh database (tests only)."""
    global DB_PATH
    DB_PATH = path
    conn = getattr(_local, 'conn', None)
    if conn is not None:
        conn.close()
    _local.conn = None
