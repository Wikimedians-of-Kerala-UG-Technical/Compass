# Known Issues and Limitations

What's approximate or missing in Compass. Read this before trusting an output or planning work. The evaluation in `EVALUATION.md` and the playbook in `eval/README.md` measure most of these.

---

## Fixed in the October 2026 rewrite (v2)

| v1 problem | Now |
|---|---|
| Topics from a 12-keyword list (zoology → nothing; "india" a topic, Nigeria not) | Wikipedia's ML topic and country labels (`cirrusdoc`) |
| enwiki only | Home wiki detected per editor; `?wiki=` for any Wikipedia |
| Tasks were keyword searches (*Orlando: A Biography* for 9 of 15 editors) | `articletopic`/`articlecountry`/your categories/near you/similar to yours × tracking categories |
| `hastemplate:` matched nested templates | Tracking categories on enwiki; mapped local templates elsewhere |
| Pageviews looked up before the geo bonus, so 5–8 of every top 10 showed 0 | Looked up for the final top 30, then re-ranked |
| Geo focus ignored counts (Kentucky for Doc James) and used historical states | Count thresholds, ranks, P576 skipped, local place inside the region |
| `qualityTier` punished vandal fighters | Reverted by others, excluding self-reverts |
| Creations guessed from summaries (20 of 648) | `ucshow=new` |
| Revisit labelled "needs more references" as "Unreferenced"; no dates | Exact labels, tag dates, new-since-your-edit, revert-risk check |
| Discover alphabetical, wrong create link, empty for monolingual editors without saying why | CX recommender + sections, Content Translation links, explicit monolingual message |
| Guide's regex section splitter gave false alarms | Parsoid HTML: uncited paragraphs and dated inline tags |
| References suggested Wikipedia articles; Semantic Scholar always 429; PubMed by title words | Removed; key-gated; topic-routed PubMed reviews; Citoid templates; already-cited excluded |
| Trends global, two dead sources, DYK chrome | Country and home-wiki top articles that need work |
| Three HTTP clients, placeholder User-Agent, `debug=True`, hard-coded API base | One client, configurable UA, env config, `VITE_API_BASE` |
| Silent partial failures | `partial` + `failed` on responses, shown in the UI |

## Added in v2.1

| Gap | Now |
|---|---|
| Internal error text (upstream URLs) sent to the browser | Logged with an id; the client gets the id only |
| `doc_James`, `Doc James` cached as different users | MediaWiki-style username normalisation |
| Cache stored with `pickle` | Tagged JSON (no code runs when a cache file is read) |
| Unbounded per-key cache locks; O(n) eviction | Locks freed after use; insertion-order eviction |
| No tests or CI | pytest (offline), vitest, ruff, GitHub Actions, nightly API probe |
| Development server only | gunicorn config, Dockerfile, Procfile, `/api/health`, static serving with deep links |
| No rate limit on Compass's own API | `COMPASS_RATE_LIMIT`, default 120/min per client |
| CORS defaulted to `*` | Dev servers only, unless configured |
| Refresh lost your place; nothing shareable | Every screen has a URL |
| Light theme read undefined design tokens (transparent top bar) | Codex light and dark tokens; dark mode |
| Search box never hid on phones (inline style beat the media query) | Fixed; top bar fits at 360 px |
| *.xxx* topped India's trends | Automated-traffic filter |

---

## Open issues

### Coverage
- **ML topic and country labels exist only on Wikipedias.** An editor who works almost only on Wikidata (e.g. Athulvis) still gets a profile from their small Wikipedia footprint. Their main value comes from Commons & Wikidata.
- **PageAssessments (quality class) exists on enwiki and a few others.** Elsewhere, feasibility relies on size alone. Lift Wing `articlequality` covers 11 wikis (not ml).
- **Tracking categories are sparse on some wikis** (mlwiki "All articles with unsourced statements": ~500 pages). Compass then uses the template, which can match nested templates.
- **Growth `hasrecommendation:` types vary by wiki.**
- **Edit-summary classification is English-only.** Tags cover the language-independent cases.

### Ranking
- The weights (`WEIGHTS` in `task_service.py`: 0.30/0.20/0.15/0.15/0.10/0.10) are still hand-set. Task feedback is now stored with each card's signals and `eval/learn_weights.py` fits weights to it, but it needs a few hundred mixed votes before the result means anything, and votes need no login, so anyone can vote on anyone's tasks. Treat fitted weights as a suggestion to test with the evaluation, not a replacement.
- "Biography" and "Media" are broad topics. For editors whose top topic is broad, the category and similar-article scopes matter most.
- Topics now weigh bytes added as well as edit count (`article_weight` in `profile_service.py`), to help editors whose recent edits are broad (Cwmhiraeth). The effect hasn't been re-measured with the evaluation harness yet.
- Newcomers (< 200 edits) get Growth's guided tasks only. Compass can't read the topics they picked on Special:Homepage (user preferences are private), so it uses their detected topics plus the whole wiki.

### Sources
- Book catalogues and Internet Archive match loosely. Their results are kept only when the title shares words with the article title, which drops noise but also drops relevant books with different titles. Google Books needs `GOOGLE_BOOKS_API_KEY`: the anonymous quota is always exhausted.

### Discover
- "Missing in your language" for monolingual editors uses English Wikipedia as the index of what's important, so it reflects English Wikipedia's coverage. For editors who only write English there is still no Discover list: Wikidata queries for "important elsewhere, missing in English" by country time out (tested: 47–62 s for India and Sweden).

### Events
- Only events with a worklist can be ranked. Worklists are new (August 2026), so many events don't have one yet.
- Private registrations aren't listed (the API only shows them to organisers).
- One wiki is ranked at a time, and at most 1,000 of its worklist articles.
- Worklist titles that don't exist yet can't be scored, so they're listed unranked.

### Live alerts
- Each Compass process keeps one EventStreams connection while anyone is subscribed, and each open tab holds one server thread. That suits tens of concurrent viewers, not thousands.
- Reverts and tags on edits (`mw-reverted`) aren't in the recentchange stream, so "your edit was reverted" isn't an alert yet.
- Browser notifications only appear while the tab is open (no service worker or email digest).

### Freshness and scale
- Caches (profile 6 h, signals 24 h, Wikidata places 7 days, trends 3 h, stats 1 h) live in memory and in one SQLite file. That suits one machine; several machines would need a shared store such as Redis. The same goes for the rate limit, which is counted per worker.
- A first visit is still slow for a very active editor: 2,000 contributions take four sequential API pages (~6 s; `uccontinue` can't be parallelised), and a place hierarchy is walked one level at a time. `backend/warm.py` pre-builds regular visitors' dashboards.
- WDQS queries can take 1–60 s and are rate-limited. Region gaps use direct P131 children only, because transitive queries over a whole state time out.
- Lift Wing and the CX recommendation API are used anonymously, which has rate limits. Register an API token for production volume.

### Interface
- Only English messages exist so far. The interface is ready for translation (`frontend/src/locales/en.json`), but translations, and a translatewiki.net setup, still need people who speak the languages.

### Not built yet
- Toolforge deployment itself (a Dockerfile, a `Procfile` and gunicorn settings are ready).
- Streaming the dashboard's slow parts (server-sent progress) instead of separate requests.
- Email digests of alerts.
