# Getting Started

## Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- An internet connection: everything is fetched live from Wikimedia APIs

No accounts or API keys are needed. Login with a Wikimedia account is optional (see below).

## Run it

### Backend (Flask on `:5000`)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt      # backend deps + pytest + ruff
cd backend
python app.py
```

Dependencies are pinned in `backend/requirements.txt`: `flask`, `flask-cors`, `requests`, `beautifulsoup4`, `gunicorn`.

| Env var | Default | Meaning |
|---|---|---|
| `FLASK_DEBUG` | off | `1` for the auto-reloader and debugger |
| `COMPASS_HOST` / `COMPASS_PORT` | `127.0.0.1` / `5000` | Bind address for `python app.py` |
| `COMPASS_CORS_ORIGINS` | the Vite dev and preview servers | Comma-separated allowed origins; `*` for a public read-only API (login then can't work cross-origin) |
| `COMPASS_CACHE_PATH` | `backend/.cache/compass.sqlite3` | Disk cache shared by restarts and workers. Empty = memory only. Delete the file to start cold |
| `COMPASS_DB_PATH` | `backend/.data/compass.db` | Compass's own data: task feedback and login sessions. Back this one up |
| `COMPASS_RATE_LIMIT` | `120/minute` | Per-client limit on `/api/*` (per worker). `0` turns it off |
| `COMPASS_TRUST_PROXY` | off | `1` behind a reverse proxy, so the rate limit sees real client addresses |
| `COMPASS_USER_AGENT` | `Compass/2.0 (repo URL)` | Add a contact address when you deploy ([User-Agent policy](https://meta.wikimedia.org/wiki/User-Agent_policy)) |
| `COMPASS_STATIC_DIR` | unset | A built `frontend/dist`; the backend then serves the app too, with deep links |
| `COMPASS_LOG_LEVEL` | `INFO` | Python log level |
| `SEMANTIC_SCHOLAR_API_KEY` | unset | Enables Semantic Scholar in Sources |
| `GOOGLE_BOOKS_API_KEY` | unset | Enables Google Books in Sources (the shared anonymous quota is always used up) |
| `COMPASS_OAUTH_CLIENT_ID` / `COMPASS_OAUTH_CLIENT_SECRET` | unset | Enable "Log in" (see below) |
| `COMPASS_OAUTH_CALLBACK` | `http://127.0.0.1:5000/api/auth/callback` | Must match the consumer's registered callback |
| `COMPASS_FRONTEND_URL` | unset | Where login returns to by default; also allowed as a return address |
| `COMPASS_SECRET_KEY` | random per process | Signs the login state cookie. Required with login and more than one worker |

### Frontend (Vite on `:5173`)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** and enter any username, e.g. `Ranjithsiji` (Malayalam), `Hog Farm` (English), or `Ravidreams` (Tamil). Every screen has a URL (`/u/Ranjithsiji/tasks?wiki=mlwiki`), so you can refresh or share a link. To point the frontend at another backend, set `VITE_API_BASE`; an empty value means the same origin.

## Tests and lint

```bash
pytest                       # backend, offline: network calls fail the test
ruff check .
cd frontend && npm test      # store, router sync and i18n key coverage
```

CI (`.github/workflows/ci.yml`) runs all three plus `npm run build` on every PR. `probe-apis.yml` runs `eval/probe_apis.py` nightly, so an upstream API change shows up as a failed run.

## Optional: login with a Wikimedia account

Login adds the editor's watchlist to Revisit and, for newcomers, Growth's task list for the topics they chose on Special:Homepage. Everything else works without it.

1. Propose an OAuth 2.0 consumer at [Special:OAuthConsumerRegistration/propose/oauth2](https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration/propose/oauth2): confidential client, grants "Basic rights" and "View your watchlist", callback `https://<your host>/api/auth/callback`.
2. Set `COMPASS_OAUTH_CLIENT_ID`, `COMPASS_OAUTH_CLIENT_SECRET`, `COMPASS_OAUTH_CALLBACK`, `COMPASS_FRONTEND_URL` and `COMPASS_SECRET_KEY`.
3. Serve the frontend and backend from the same site (the Docker image does), or list the frontend in `COMPASS_CORS_ORIGINS`: the session cookie is `SameSite=Lax`.

Tokens stay on the server, in `COMPASS_DB_PATH`; the browser only holds an opaque session id.

## What to expect

| Stage | Typical time |
|---|---|
| Profile | 10–30 s (then cached for 6 h) |
| Tasks, Revisit, Geo, Trends | 5–40 s each, in parallel |
| Discover, Commons & Wikidata | 5–25 s, after Geo |
| Stats | 2–5 s, when the Stats view is opened |

The dashboard appears as soon as the profile is ready. Tasks first appear from topics and categories, and "near you" tasks are added once Geo resolves. Editors who visit often can be pre-warmed: `python backend/warm.py Ranjithsiji "Netha Hussain"` (run it from cron every few hours).

## Check it works

```bash
curl "http://127.0.0.1:5000/api/health"
curl "http://127.0.0.1:5000/api/profile/Ranjithsiji"          # homeWiki: mlwiki, topics: Films…
curl "http://127.0.0.1:5000/api/tasks/Ranjithsiji"            # Malayalam articles needing work
curl "http://127.0.0.1:5000/api/article/Tuberculosis/guide"   # dated dead links, no false "short section"
python eval/probe_apis.py                                     # every external API still answers
```

## Troubleshooting

- **A user returns 404:** either no Wikimedia account has that name, or the account has no edits on the requested `wiki`. Spaces and underscores both work, and the first letter is capitalised for you, but the rest is case-sensitive (`Doc James`, not `doc james`).
- **`partial: true`:** a sub-source failed, usually from rate limiting. Wait a minute and refresh.
- **HTTP 429 from Compass:** you hit `COMPASS_RATE_LIMIT`. Raise it, or set `0` for local testing.
- **A 500 with an error id:** the full traceback is in the server log under that id.
- **Slow first load for a very active editor:** expected. The profile is cached afterwards.

## Load testing

`locustfile.py` drives the Guide endpoint with random titles. Start the backend with `STRESS_TEST=1` so the Guide returns canned data instead of calling Wikimedia:

```bash
STRESS_TEST=1 COMPASS_RATE_LIMIT=0 python backend/app.py
locust -f locustfile.py --host http://127.0.0.1:5000
```

## Production

**Docker** (API and app in one image, data in a volume):

```bash
docker build -t compass .
docker run -p 8000:8000 -v compass-data:/data -e COMPASS_USER_AGENT="Compass/2.1 (https://…; you@example.org)" compass
```

**Without Docker:** `npm run build` in `frontend/`, then from `backend/`:

```bash
COMPASS_STATIC_DIR=../frontend/dist gunicorn -c gunicorn.conf.py wsgi:app
```

`gunicorn.conf.py` uses threaded workers (2 × 32 threads by default; `COMPASS_WORKERS`, `COMPASS_THREADS`, `COMPASS_TIMEOUT`, `PORT`). Threads matter because requests mostly wait on Wikimedia, and each open live-alerts tab holds one thread. A `Procfile` is included for buildpack hosts such as Toolforge's build service.

- Set `COMPASS_USER_AGENT` with a contact address, and `COMPASS_CORS_ORIGINS` to the site's own origin.
- Behind nginx or another proxy, set `COMPASS_TRUST_PROXY=1` and turn off response buffering for `/api/alerts/` (the app already sends `X-Accel-Buffering: no`).
- Workers share the SQLite cache and data files; each also keeps its own memory cache and rate-limit counters.
