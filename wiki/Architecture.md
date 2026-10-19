# Architecture

## Design principles

1. **Any wiki, not just English.** Every service takes a `dbname`. The editor's home wiki (most edits) is the default, so a Malayalam, Tamil or Swedish editor gets results from their own Wikipedia.
2. **Use Wikipedia's own signals.** Topics, countries, quality, maintenance tags and recommendations come from what Wikimedia already computes: ML labels in the search index (`cirrusdoc`), tracking categories, PageAssessments, Growth suggestions and Lift Wing models. There are no keyword lists.
3. **Routes are thin, services are thick.** `routes/` parses parameters and serialises JSON. All logic is in `services/`.
4. **One client, one cache.** All HTTP goes through `services/wiki.py`, which handles User-Agent, retries, POST batching and per-wiki hosts. Results are cached with a TTL, in memory and in a SQLite file (`COMPASS_CACHE_PATH`), so restarts and other workers start warm.
5. **Say when something failed.** Sub-source failures are reported as `partial: true` (with `failed`) instead of silently becoming empty lists.

---

## System overview

```mermaid
flowchart TB
    subgraph Browser["Frontend — Vue 3 + Pinia"]
        Views["Views: Overview, Tasks, Revisit,<br/>Discover, Commons & Wikidata, Guide"]
        Store["appStore.js<br/>state + load order"]
        Views --> Store
    end

    Store -->|"fetch, CORS"| API

    subgraph API["Backend — Flask"]
        Routes["routes/"]
        Services["services/"]
        Client["wiki.py<br/>client + TTL cache"]
        Routes --> Services --> Client
    end

    Client --> MW["MediaWiki Action + REST API<br/>(any wiki; cirrusdoc, search,<br/>Parsoid HTML)"]
    Client --> WD["Wikidata API + Query Service"]
    Client --> PV["Pageviews"]
    Client --> LW["Lift Wing<br/>(revert risk, CX recommendations)"]
    Client --> CX["cxserver, Citoid"]
    Client --> ACAD["PubMed, OpenAlex, CrossRef"]
```

---

## Backend module map

| Module | Responsibility |
|---|---|
| `app.py` | App factory. Auto-registers every blueprint in `routes/`; central error handlers; rate limit; optional static frontend with deep-link fallback; `/api/health`. Config through env vars (see [[Getting-Started]]). |
| `wsgi.py`, `gunicorn.conf.py` | Production entry point and threaded-worker settings. |
| `warm.py` | Pre-builds the cached dashboard for given usernames (cron). |
| `services/wiki.py` | The HTTP client: `api(dbname, params, post, token)`, `api_pages` (50-title batches over POST), `search`, `get_json`/`post_json`, host and URL helpers, `normalize_username`, `UserError`, and `TTLCache` (thread-safe, with per-key compute locks that are freed after use; named caches are also written to SQLite as tagged JSON). |
| `services/store.py` | Compass's own SQLite data (`COMPASS_DB_PATH`): feedback and login sessions. Never purged. |
| `services/ratelimit.py` | Sliding-window limit per client address, per process. |
| `services/signals.py` | Per-article signals from `prop=cirrusdoc|pageassessments|info`: ML topics and country, Growth recommendations, popularity, incoming links, size, coordinates, categories, templates, quality class, protection. Cached 24 h. |
| `services/maintenance.py` | Maintenance issues on any wiki. English tracking categories and templates are mapped to local names through interlanguage links. `issues_of(sig)` and `search_filter(key)`. |
| `services/profile_service.py` | Home wiki, contributions, creations, Babel, topic/country aggregation, edit types from tags, reverted-by-others. Cached 6 h. |
| `services/task_service.py` | Candidate search (scope × filter), signal-based ranking (`WEIGHTS`), pageviews, diversification; guided mode for newcomers. |
| `services/feedback_service.py` | Task votes with their ranking signals; checks later edits; training rows for `eval/learn_weights.py`. |
| `services/stats_service.py` | Streak, last-30-day activity and readers reached, from live contributions. |
| `services/event_service.py` | Events: resolve an Event Registration event, read its worklist and participants, rank the worklist for one editor. |
| `services/alerts_service.py` | `AlertHub`: one shared EventStreams connection, routing edits and tracking-category changes to subscriber queues. |
| `services/auth_service.py` | Optional OAuth 2 login: token exchange and refresh, sessions, watchlist, Special:Homepage choices, `list=growthtasks`. |
| `services/geo_service.py` | Wikidata P131 hierarchy walk with ranks and P576 handling; focus selection. |
| `services/revisit_service.py` | Tags on the editor's own articles, with dates; new since last edit; revert risk of the latest edit. |
| `services/discover_service.py` | CX recommendation API (articles, sections), WDQS region gaps, and "missing in your language" for monolingual editors (CirrusSearch on enwiki + langlinks). |
| `services/crossproject_service.py` | Unused Commons uploads, Wikidata label/description gaps, CampaignEvents. |
| `services/article_service.py` | Parsoid HTML analysis, Wikidata comparison, missing sections via cxserver. |
| `services/references_service.py` | Topic-routed PubMed/OpenAlex/CrossRef search, plus Open Library, Internet Archive and Google Books for non-medical articles; Citoid citations. |
| `services/trends_service.py` | `top-per-country` and per-wiki top articles filtered to those needing work, minus automated traffic (desktop share); Current events headlines. |
| `data/countries.json` | Country name (as the article-country model labels them) → ISO alpha-2, alpha-3 and QID. Generated from Wikidata (P297/P298, no P576). |

---

## Request flow

```mermaid
sequenceDiagram
    participant S as appStore
    participant B as Backend

    S->>B: GET /api/profile/{user}
    Note over B: home wiki, 2,000 contribs,<br/>cirrusdoc on ~200 articles
    B-->>S: profile
    par
        S->>B: GET /api/trends?country=IN&wiki=mlwiki
        S->>B: GET /api/revisit/{user}
        S->>B: GET /api/tasks/{user}
        S->>B: GET /api/geo/{user}
    end
    B-->>S: geo (focus.region, focus.local)
    par
        S->>B: GET /api/tasks/{user}?lat&lon&place   (adds "near you")
        S->>B: GET /api/discover/{user}?region&local
        S->>B: GET /api/contribute/{user}?place
    end
```

The profile is cached, so the parallel calls reuse it rather than fetching contributions again. `sessionSeq` and `tasksRequestSeq` stop a slow response for an earlier user, or an earlier wiki, from overwriting a newer one. See [[Frontend-State]].

---

## Error handling

| Layer | Convention |
|---|---|
| Route | Routes don't catch errors. `UserError` → its status (404 by default, 400 for malformed input) with its message; any other exception is logged with an id and returns 500 with only that id |
| Service (sub-source) | Catch, record in `failed`, set `partial: true`, and continue |
| Frontend | Per-feature `*Error` state; a warning banner when `partial` is set |
