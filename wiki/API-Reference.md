# API Reference

Base URL in development: `http://127.0.0.1:5000`

All endpoints are `GET`, unauthenticated, and return JSON. CORS is open (`flask-cors` with default settings).

## Endpoint index

| Endpoint | Purpose | Typical latency |
|---|---|---|
| [`/api/profile/<username>`](#apiprofileusername) | Build an editor profile | Slow (seconds to a minute) |
| [`/api/tasks`](#apitasks) | Ranked maintenance recommendations | Moderate |
| [`/api/geo/<username>`](#apigeousername) | Resolve geographic focus | **Slowest** (a minute or more) |
| [`/api/revisit/<username>`](#apirevisitusername) | The user's own decayed articles | Fast |
| [`/api/discover/<username>`](#apidiscoverusername) | Cross-language article gaps | Slow |
| [`/api/trends`](#apitrends) | Current events and trending pages | Fast |
| [`/api/article/<title>/guide`](#apiarticletitleguide) | Structural analysis | Fast |
| [`/api/article/<title>/references`](#apiarticletitlereferences) | Related Wikipedia articles | Moderate |
| [`/api/article/<title>/external-references`](#apiarticletitleexternal-references) | Academic citations | Moderate |

## Error conventions

| Status | Meaning | Body |
|---|---|---|
| `200` | Success | The documented payload |
| `404` | User has no edits | `{"error": "No edits found for \"x\"."}` |
| `500` | Upstream or internal failure | `{"error": "Something went wrong: …"}` |

The `/api/article/*` endpoints are the exception: on failure they return **500 with a shaped fallback object** (empty `suggestions`, `results`, etc.) so the UI always has a renderable structure.

---

## `/api/profile/<username>`

Full detail: [[Feature-Editor-Profile]]

Builds an editor profile from up to 20,000 contributions.

**Response**

| Field | Type | Notes |
|---|---|---|
| `username` | string | |
| `total` | int | **Global** cross-wiki edit count from Meta |
| `uniqueArticles` | int | Distinct ns=0 titles in the fetched window |
| `editTypes` | object | Label → count, 17 possible labels |
| `topTopics` | string[] | Top 3; `["general"]` if nothing matched |
| `topGeo` | string[] | Legacy keyword geography; superseded by `/api/geo` |
| `qualityTier` | string | `high` \| `medium` \| `developing` |
| `heavilyEdited` | object[] | `{title, count}`, 3+ edits, max 15 |
| `createdArticles` | string[] | Max 20 |
| `recentEdits` | object[] | 15 newest with `diffUrl` and `articleUrl` |

---

## `/api/tasks`

Full detail: [[Feature-Task-Recommendations]]

**Query parameters**

| Param | Type | Required | Notes |
|---|---|---|---|
| `topics` | comma-separated | No | **Max 5.** Omitting falls back to a hardcoded generic list |
| `editTypes` | comma-separated | No | Drives the affinity bonus |
| `geo` | string | No | One place name; adds a search topic and a +0.40 bonus |

**Response** — a JSON **array** (not an object), pre-sorted:

| Field | Type | Notes |
|---|---|---|
| `title` | string | Article title |
| `type` | string | `add_refs` \| `fix_orphan` \| `add_citations` \| `expand_stub` |
| `topic` | string | Which topic surfaced it |
| `reason` | string | Human-readable explanation |
| `meta` | object | `{label, effort, min}` |
| `score` | float | Composite score, 3 decimals |
| `pageviews` | int | 30-day daily average; `0` if not enriched |
| `trend` | int | Percent change, 7d vs prior 7d |
| `staleDays` | int | Days since last touched; `0` if not enriched |

> `pageviews`/`staleDays` are `0` for candidates outside the top-16 enrichment window — this means "not measured," not "zero views."

---

## `/api/geo/<username>`

Full detail: [[Feature-Geographic-Focus]]

| Field | Type | Notes |
|---|---|---|
| `articlesWithGeo` | int | Articles that resolved to a place |
| `topPlaces` | object[] | `{name, count}`, max 12, all hierarchy levels |
| `topCountries` | object[] | `{name, count}`, max 3 |

---

## `/api/revisit/<username>`

Full detail: [[Feature-Revisit]]

**Query parameters** — both JSON-encoded, supplied by the frontend from the profile response.

| Param | Format | Cap |
|---|---|---|
| `watch` | `[{title, count}]` | 15 |
| `mine` | `[title]` | 20 |

Malformed JSON degrades to an empty list rather than erroring.

**Response**

```json
{ "username": "...", "tasks": [
  { "title": "...", "source": "watchlist|followup",
    "tags": [{"key": "...", "label": "..."}], "reason": "..." }
]}
```

Sorted by number of tags, descending.

---

## `/api/discover/<username>`

Full detail: [[Feature-Discover]]

| Field | Type | Notes |
|---|---|---|
| `editsFetched` / `uniquePages` / `uniqueCategories` / `categoriesWithQid` | int | Diagnostics |
| `categories` | object[] | `{name, qid, wikidataUrl, pageCount}` |
| `userWikis` | object[] | `{dbname, lang, url, editcount}`, ≥10 edits |
| `suggestedArticles` | object[] | `{title, qid, wikidataUrl, fromCategory, categoryWeight, existsIn, missingIn}` |
| `skippedMegaCategories` | string[] | Categories over 3,000 pages |

Empty `suggestedArticles` is normal for monolingual editors.

---

## `/api/trends`

Full detail: [[Feature-Trends]]

```json
{
  "news":     [{ "text": "...", "articles": ["..."], "source": "current_events" }],
  "trending": [{ "title": "...", "views": 1200431, "source": "wiki_trending" }]
}
```

`news.source` ∈ `current_events` | `recent_deaths` | `ongoing` | `dyk`.

---

## `/api/article/<title>/guide`

Full detail: [[Feature-Article-Guide]]

| Field | Type | Notes |
|---|---|---|
| `articleType` | string | `biography` \| `medical` \| `place` \| `event` \| `general` |
| `sections` | object[] | `{name, level, index, charCount, status, refCount}` |
| `missingExpected` | string[] | Expected-but-absent sections for this type |
| `suggestions` | object[] | `{type, text}` |
| `currentSize` | int | Wikitext length in characters |
| `totalRefs` | int | Count of `<ref` tags |
| `hasInfobox` / `hasImages` | bool | |
| `cats` | string[] | Lowercased categories |

## `/api/article/<title>/references`

| Param | Default | Notes |
|---|---|---|
| `offset` | `0` | Page through results, 5 per page |

Returns `{results[], nextOffset, total}`. Each result includes `whatToEdit` and `missingSections` — analysis of *that* article, not the original.

## `/api/article/<title>/external-references`

No parameters. Returns `{results: [{title, url, citations, source}]}` where `source` ∈ `Semantic Scholar` | `CrossRef` | `PubMed`. Round-robin interleaved and deduplicated.

---

## Adding a new endpoint

`app.py` auto-discovers blueprints:

```python
for _, name, _ in pkgutil.iter_modules(routes.__path__):
    mod = importlib.import_module(f"routes.{name}")
    if hasattr(mod, "bp"):
        app.register_blueprint(mod.bp)
```

Drop a file in `backend/routes/` that exposes a `bp` — no registration step needed.
