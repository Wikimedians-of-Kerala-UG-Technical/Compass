"""Production server settings. Every value can be overridden with an environment variable.

Threads, not processes, do most of the work: a request mostly waits on Wikimedia APIs,
and live alerts (/api/alerts/.../stream) hold one thread per open tab. Each worker has
its own memory cache and rate-limit counters; the SQLite cache is shared.
"""
import os

bind = os.environ.get('COMPASS_BIND', f"0.0.0.0:{os.environ.get('PORT', '8000')}")
workers = int(os.environ.get('COMPASS_WORKERS', 2))
worker_class = 'gthread'
threads = int(os.environ.get('COMPASS_THREADS', 32))
# A cold dashboard for a very active editor can take a minute (Wikidata Query Service).
timeout = int(os.environ.get('COMPASS_TIMEOUT', 180))
graceful_timeout = 30
accesslog = '-'
