# Getting Started

## Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- An internet connection: everything is fetched live from Wikimedia APIs

No database, no accounts and no API keys are needed.

## Run it

### Backend (Flask on `:5000`)

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Dependencies: `flask`, `flask-cors`, `requests`, `beautifulsoup4`.

| Env var | Default | Meaning |
|---|---|---|
| `FLASK_DEBUG` | off | `1` for the auto-reloader and debugger |
| `COMPASS_HOST` / `COMPASS_PORT` | `127.0.0.1` / `5000` | Bind address |
| `COMPASS_CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `COMPASS_USER_AGENT` | `Compass/2.0 (repo URL)` | Add a contact address when you deploy ([User-Agent policy](https://meta.wikimedia.org/wiki/User-Agent_policy)) |
| `SEMANTIC_SCHOLAR_API_KEY` | unset | Enables Semantic Scholar in Sources |

### Frontend (Vite on `:5173`)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** and enter any username, e.g. `Ranjithsiji` (Malayalam), `Hog Farm` (English), or `Ravidreams` (Tamil). To point the frontend at another backend, set `VITE_API_BASE`.

## What to expect

| Stage | Typical time |
|---|---|
| Profile | 10–30 s (then cached for 6 h) |
| Tasks, Revisit, Geo, Trends | 5–40 s each, in parallel |
| Discover, Commons & Wikidata | 5–25 s, after Geo |

The dashboard appears as soon as the profile is ready. Tasks first appear from topics and categories, and "near you" tasks are added once Geo resolves.

## Check it works

```bash
curl "http://127.0.0.1:5000/api/profile/Ranjithsiji"          # homeWiki: mlwiki, topics: Films…
curl "http://127.0.0.1:5000/api/tasks/Ranjithsiji"            # Malayalam articles needing work
curl "http://127.0.0.1:5000/api/article/Tuberculosis/guide"   # dated dead links, no false "short section"
python eval/probe_apis.py                                     # every external API still answers
```

## Troubleshooting

- **A user returns 404:** either no Wikimedia account has that name (spaces or underscores both work), or the account has no edits on the requested `wiki`.
- **`partial: true`:** a sub-source failed, usually from rate limiting. Wait a minute and refresh.
- **Slow first load for a very active editor:** expected. The profile is cached afterwards.

## Load testing

`locustfile.py` drives the Guide endpoint. Start the backend with `STRESS_TEST=1` so it returns canned data instead of calling Wikimedia:

```bash
STRESS_TEST=1 python backend/app.py
locust -f locustfile.py
```

## Production notes

- Run under a WSGI server (e.g. `gunicorn -w 2 --threads 8 'app:create_app()'`). The in-memory caches are per process.
- Set `COMPASS_USER_AGENT` with a contact address, and `COMPASS_CORS_ORIGINS` to your frontend's origin.
- `npm run build` writes `frontend/dist`. Build it with `VITE_API_BASE` set to the deployed backend.
