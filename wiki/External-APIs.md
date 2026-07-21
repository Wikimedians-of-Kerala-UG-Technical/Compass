# External APIs

Every piece of data in Compass comes from a public API. Nothing is stored, scraped from HTML pages we don't control, or authenticated.

## Summary

| API | Base URL | Used for | Auth |
|---|---|---|---|
| MediaWiki Action API (en.wikipedia) | `https://en.wikipedia.org/w/api.php` | Contributions, categories, search, article parsing, page info | None |
| MediaWiki Action API (Meta) | `https://meta.wikimedia.org/w/api.php` | Cross-wiki edit counts, user's languages | None |
| Wikidata Action API | `https://www.wikidata.org/w/api.php` | Place hierarchy, sitelinks | None |
| Wikimedia Pageviews REST | `https://wikimedia.org/api/rest_v1` | Article popularity, trending pages | None |
| Semantic Scholar | `https://api.semanticscholar.org/graph/v1` | Academic reference suggestions | None |
| CrossRef | `https://api.crossref.org/works` | Academic reference suggestions | None |
| PubMed E-utilities | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils` | Biomedical reference suggestions | None |

All Wikimedia requests share one `requests.Session` carrying a descriptive `User-Agent`, per [Wikimedia's API etiquette](https://www.mediawiki.org/wiki/API:Etiquette).

---

## MediaWiki Action API

### `list=usercontribs` — the foundation of everything

Fetches a user's edit history. This single call powers Profile, Geo, Discover, and Revisit.

| Parameter | Value | Why |
|---|---|---|
| `ucuser` | username | Target editor |
| `uclimit` | `500` | API hard cap per page |
| `ucprop` | `title\|timestamp\|comment\|sizediff\|tags\|size\|ids` | `comment`+`tags`+`sizediff` drive edit classification; `ids` builds diff links |
| `ucdir` | `older` | Newest first, so truncation drops the *oldest* edits |
| `uccontinue` | cursor | Pagination |

Paginated in a loop with `time.sleep(0.25)` between pages. Different callers request different depths:

| Caller | Limit | Rationale |
|---|---|---|
| Profile | 20,000 | Needs full history for accurate edit-type and quality stats |
| Discover | 1,000 | Only needs a representative category sample |
| Geo | 1,000 | Only needs a representative place sample |

Raises `ValueError` when a user has zero edits → surfaces as a **404**.

### `prop=categories` — topic and issue signals

| Parameter | Value | Notes |
|---|---|---|
| `titles` | up to 50, pipe-joined | API hard cap |
| `cllimit` | `max` | All categories per page |
| `clshow` | `!hidden` | **Profile only.** Hidden categories are maintenance bookkeeping, not topic signal |

Revisit deliberately **omits** `clshow=!hidden` — it *wants* the hidden maintenance-tracking categories, since those are exactly what flag a decayed article.

### `list=search` — candidate task discovery

| Parameter | Value | Notes |
|---|---|---|
| `srsearch` | `hastemplate:"Unreferenced" india` | The `hastemplate:` operator finds articles carrying a maintenance template |
| `srlimit` | `4` (tasks) / `5` (guide refs) | Kept small — each result triggers follow-up calls |
| `srnamespace` | `0` | Articles only, no Talk/User pages |
| `srprop` | `snippet\|size\|wordcount` | |

### `action=parse` — article structure

Used by the Article Guide. `prop=sections|wikitext|categories`, `redirects=true`.

The raw wikitext is what makes section-level analysis possible — it's split on heading regex to measure per-section length and count `<ref` tags.

### `prop=info` — staleness and length

- Scoring uses `touched` (last modification timestamp) → days since last edit.
- Revisit uses `length` (bytes) → flags self-created articles under 4,000 bytes as expandable.

### `list=categorymembers` — expanding a category

Used by Discover (candidate articles), Trends (recent deaths, ongoing events), and regional stub tasks. Always `cmnamespace=0`. Single page, no deep pagination — this is sampling, not crawling.

### `meta=globaluserinfo` (Meta wiki)

`guiprop=merged` returns per-wiki edit counts across the user's unified account. Two derived signals:

- **Total edit count** — summed across every merged wiki (the headline profile number).
- **Known languages** — wikis matching `^https://([a-z0-9-]+)\.wikipedia\.org$` with ≥10 edits. Powers Discover's "missing in your languages" logic. The regex intentionally excludes Commons, Wikidata, and Meta, which aren't language editions.

---

## Wikidata API

### `wbgetentities` with `props=claims|labels`

Powers [[Feature-Geographic-Focus]]. The properties we read:

| Property | Meaning | Role |
|---|---|---|
| `P31` | instance of | Detects humans (`Q5`) |
| `P131` | located in admin. entity | The **main hierarchy edge** we walk upward |
| `P17` | country | Fallback edge when `P131` is absent |
| `P19` | place of birth | Anchor for a person |
| `P27` | country of citizenship | Fallback anchor for a person |
| `P297` | ISO 3166-1 alpha-2 code | Presence ⇒ this entity **is a country** ⇒ stop walking |
| `P300` | ISO 3166-2 code | Presence ⇒ first-level admin division (state/province) |

Using `P297`/`P300` presence as a type test is a deliberate shortcut — it avoids a separate class-hierarchy query, since only countries have an ISO country code.

### `wbgetentities` with `props=sitelinks`

Returns which wikis already have an article for a given item. Discover diffs this against the user's known wikis to find translation gaps.

Both are batched at 50 IDs with `time.sleep(0.25)` between batches.

---

## Wikimedia Pageviews REST API

### Per-article views (impact signal)

```
/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{title}/daily/{start}/{end}
```

A 30-day window ending yesterday (today's data is incomplete). Two derived numbers:

- **`avg`** — mean daily views → normalized to a 0–1 impact score at `min(avg / 500, 1)`.
- **`trend`** — `(last 7 days − prior 7 days) / prior 7 days × 100`, a percentage. Above +30% earns a small bonus.

Called concurrently via `ThreadPoolExecutor(max_workers=8)`, but only for the **top 16 pre-ranked candidates** — see [[Feature-Task-Recommendations]].

### Top articles (Trends)

```
/metrics/pageviews/top/en.wikipedia/all-access/{yyyy}/{mm}/{dd}
```

Yesterday's most-viewed pages. `Special:`, `Wikipedia:`, `Portal:`, and `Main_Page` are filtered out; top 30 kept.

---

## Academic reference APIs

Used only by `/api/article/<title>/external-references`. All three are queried in parallel via `ThreadPoolExecutor(max_workers=3)`, each with a 5s timeout.

| Source | Endpoint | Query strategy |
|---|---|---|
| Semantic Scholar | `/paper/search` | `query=title`, `limit=5`, fields `title,url,citationCount` |
| CrossRef | `/works` | `query.bibliographic=title`, `rows=5` |
| PubMed | `esearch` → `esummary` | `db=pubmed`, `retmax=5`, two-step ID-then-detail fetch |

Two deliberate tuning decisions:

- **CrossRef uses `query.bibliographic`, not `query`**, and omits `sort`. Sorting by `is-referenced-by-count` surfaced famous-but-irrelevant papers for generic titles; default relevance ranking is better.
- **PubMed is skipped entirely** unless the article title matches a medical keyword list (`MEDICAL_HINTS`). Querying a biomedical index for a place or a film reliably returns noise.

Results are **interleaved round-robin** across sources rather than globally sorted, so each source's own relevance ranking is preserved, then deduplicated case-insensitively by title.
