"""Per-client rate limit for Compass's own API.

One busy client shouldn't use up the anonymous Wikidata, Lift Wing and pageviews
allowance that every other user shares. Limits are kept in memory, per process: with
several gunicorn workers each worker counts separately, which is approximate but
enough to stop a runaway script.

COMPASS_RATE_LIMIT is "<requests>/<second|minute|hour>"; "0" or "" turns it off.
"""
import os
import threading
import time
from collections import deque

WINDOWS = {'second': 1, 'minute': 60, 'hour': 3600}


def parse(spec):
    """'120/minute' -> (120, 60). None when disabled."""
    spec = (spec or '').strip()
    if not spec or spec == '0':
        return None
    count, _, unit = spec.partition('/')
    return int(count), WINDOWS[unit.strip().lower() or 'minute']


class RateLimiter:
    def __init__(self, limit, window, max_clients=10000):
        self.limit, self.window, self.max_clients = limit, window, max_clients
        self._hits = {}
        self._lock = threading.Lock()

    def check(self, client, now=None):
        """Records a request. Returns 0 if allowed, else seconds until the client may retry."""
        now = time.time() if now is None else now
        with self._lock:
            hits = self._hits.get(client)
            if hits is None:
                if len(self._hits) >= self.max_clients:
                    self._prune(now)
                hits = self._hits[client] = deque()
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return max(int(hits[0] + self.window - now) + 1, 1)
            hits.append(now)
            return 0

    def _prune(self, now):
        for client in [c for c, h in self._hits.items() if not h or h[-1] <= now - self.window]:
            del self._hits[client]


def from_env():
    parsed = parse(os.environ.get('COMPASS_RATE_LIMIT', '120/minute'))
    return RateLimiter(*parsed) if parsed else None
