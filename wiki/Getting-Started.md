# Getting Started

## Prerequisites

- **Python 3.8+**
- **Node.js 18+** (Vite 8 requires a modern Node)
- An internet connection — everything is fetched live from Wikimedia APIs

No database, no API keys, no accounts, no `.env` file.

---

## Run it

### Backend — Flask on `:5000`

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Dependencies are just `flask`, `flask-cors`, `requests`. Runs with `debug=True` and `threaded=True` — threading matters, since several endpoints use thread pools for parallel API calls.

### Frontend — Vite on `:5173`

```bash
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173** and enter any public Wikipedia username (try `ranjithsiji` or `Jimbo_Wales`).

> Start the backend first. The frontend hardcodes `API_BASE = 'http://127.0.0.1:5000'` in `src/api.js`.

---

## What to expect on first load

Load times vary a lot by endpoint — this is normal, not a bug:

| Stage | Typical wait | Why |
|---|---|---|
| Profile | seconds → a minute | Pages through up to 20,000 contributions |
| Trends | ~1s | Five parallel fetches |
| Tasks (pass 1) | seconds | ~12–20 sequential searches |
| Revisit | ~1s | Two batched category lookups |
| Discover | slow | Category expansion + Wikidata sitelinks |
| Geo | **a minute or more** | Serial Wikidata hierarchy walk with rate-limit sleeps |

The dashboard appears as soon as the profile resolves; everything else fills in progressively. Tasks appear personalized by topic first, then re-rank once geo resolves.

---

## Verifying it works

Hit the API directly:

```bash
curl "http://127.0.0.1:5000/api/profile/ranjithsiji"
curl "http://127.0.0.1:5000/api/tasks?topics=india,culture,history&editTypes=references,linking&geo=Kerala"
curl "http://127.0.0.1:5000/api/geo/ranjithsiji"
```

**Sanity check:** the `/api/tasks` response should contain articles matching the topics you passed. If you see generic `science` / `biography` / `technology` results, `topics` didn't reach the backend — see [[Known-Issues-and-Limitations]].

---

## Troubleshooting

### Tasks come back empty or half-filled

Almost always Wikimedia rate limiting. Both MediaWiki helpers now retry on HTTP 429 with `Retry-After` backoff, but sustained hammering (rapid refreshes, load tests) can still exhaust retries. Wait a minute and retry.

Historically this was the most confusing failure mode in the app, because throttling was silently swallowed and looked identical to "no results found."

### Port 5173 already in use

Vite will pick the next free port and print it. Either use that URL or stop the other process.

### CORS errors in the console

The backend isn't running, or isn't on `:5000`. `flask-cors` is enabled with permissive defaults, so genuine CORS misconfiguration is unlikely.

### A user returns 404

`{"error": "No edits found for \"x\"."}` means exactly that. Usernames are case-sensitive and need underscores for spaces (`Jimbo_Wales`).

---

## Load testing

`locustfile.py` at the repo root drives the article endpoints. **Set `STRESS_TEST=1` before running it** — that makes `article_service` return canned fixtures with simulated latency instead of calling Wikipedia, which protects the project's IP from being blocked.

```bash
STRESS_TEST=1 python backend/app.py     # separate terminal
locust -f locustfile.py
```

---

## Production notes

Nothing here is production-ready as-is:

- `app.py` runs Flask's dev server with `debug=True`. Use a real WSGI server.
- `API_BASE` is hardcoded in `src/api.js` and needs to become an environment variable.
- `flask-cors` is fully open.
- The `User-Agent` strings in `http_client.py` and `article_service.py` contain placeholder contact URLs. [Wikimedia's API etiquette](https://www.mediawiki.org/wiki/API:Etiquette) expects a real contact address — fix these before running at any volume.
- `lru_cache` on article analysis is per-process and never invalidated.

## Building for production

```bash
cd frontend
npm run build      # outputs to frontend/dist
```
