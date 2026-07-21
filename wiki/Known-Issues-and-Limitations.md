# Known Issues and Limitations

An honest inventory of what's approximate, fragile, or outright broken. Read this before trusting any output or planning work.

---

## Recently fixed

Kept here because the failure modes are instructive.

### The generic-feed bug

**Symptom:** the Tasks page showed a global generic feed (science, history, geography, biography, technology) for every user regardless of their profile.

**Cause:** `api.js`'s `getTasks(geo)` accepted and forwarded **only** `geo`. The user's `topics` and `editTypes` — both already computed and sitting in the profile response — were never sent. Three consequences:

1. `topics` empty ⇒ the backend fell back to its hardcoded `GENERIC_TOPICS` list for candidate *search*. That list **was** the generic feed.
2. `topic_weight` empty ⇒ `topic_score()` returned a flat `0.2` for everything, making the formula's **largest term (0.35)** a constant that contributed nothing to ranking.
3. `edit_type_set` empty ⇒ the affinity term was always `0`.

Roughly 45% of the scoring formula was inert.

**Fix:** `getTasks({topics, editTypes, geo})` now forwards all three, sourced from `profile.topTopics` and a new `topEditTypes` getter.

### Tasks stuck behind geo resolution

**Cause:** `loadTasks()` was called only from `fetchGeo()`'s `.finally`. If geo failed, tasks loaded with no geo and were **never retried** — a permanently degraded feed. If geo succeeded, the user waited a minute-plus staring at a spinner.

**Fix:** two-pass loading — immediate profile-based pass, then a geo-weighted re-rank. See [[Frontend-State]].

### Silent rate-limit degradation

**Cause:** `trends_service.wiki_get` had no retry and no timeout. Callers wrap it in `except Exception: return []`, so an HTTP 429 became "no results." Observed live: the same request returned **54 tasks, then 0, then 19** on consecutive calls.

**Fix:** `wiki_get` now retries on 429 with `Retry-After` backoff, matching `profile_service._wiki_get`.

---

## Open issues

### Scoring

**Effort and affinity are effectively decorative.** Both are computed as `0.1 if condition else 0`, then multiplied by `0.1` in the composite — a real maximum contribution of **0.01**, roughly 40× smaller than their stated coefficients. Meanwhile `staleness` and `pageview_score` are true 0–1 values, so their coefficients apply as written. Either the bonuses should be `1.0` flags or the coefficients should be removed. Fixing it shifts every score, so it hasn't been changed silently.

**The geo bonus is a flat cliff on an exact string match.** `task.topic == geo` means an article surfaced under "Ernakulam district" earns nothing when `geo` is "Kerala" — even though both came from the same resolved chain. And a place edited 112 times scores identically to one edited 3 times. The endpoint already returns weighted `topPlaces`; the ranker should consume the whole list with count-scaled weights instead of one string.

**Enrichment is capped at 16 candidates.** Anything ranked below that on topic+urgency alone gets `pageviews = 0` and `staleDays = 0` — so a hugely popular article can never climb into contention. Intentional latency bound, but it does mean `pageviews: 0` is ambiguous between "unmeasured" and "unpopular."

**Diversification caps at 12 per type**, but with only 3–4 task types in play, the cap rarely binds.

### Candidate generation

**The geo candidate pool is small.** At most ~12 search results plus 5 stubs, versus ~48 from profile topics. Regional tasks win on bonus, not volume.

**Regional stubs depend on an exact naming convention.** `Category:{place} stubs` exists for "Kerala" but not for most places. Silent no-op otherwise — correct behavior, but coverage is thin.

**Dedup order penalizes geo.** Topics are searched before `geo`, and a global `seen` set means an article already found under `india` never reappears under `Kerala`.

### Profile accuracy

**Edit classification depends on edit summaries.** Editors who leave them blank collapse into `minor`/`general`, gutting their affinity signal. There's no fallback to diff analysis.

**Topics come from a hardcoded 12-entry keyword list** that is Anglophone- and India-skewed (`india` is a topic; Brazil and Nigeria are not). Substring matching also produces false positives.

**Only 50 articles are sampled for categories**, so topic detection reflects recent focus rather than lifetime expertise.

**`qualityTier` measures the wrong thing.** It's the rate of the user's *own* edits classified as reverts — not the rate at which their edits *were reverted by others*, which is what "quality" implies.

**`topGeo` is dead weight.** The hardcoded 8-region keyword geography is superseded by `/api/geo` but still computed and returned.

### Reliability

**Every external call is wrapped in a bare `except`.** Partial failures are invisible — a response with 19 tasks instead of 54 looks identical to a genuinely small result set. There's no `partial: true` flag and no way for the UI to say "some sources failed."

**`geoError` is never surfaced in the UI.** If geo fails, the user silently gets a non-regional feed with no explanation.

**Three separate HTTP clients** with three retry strategies: `http_client.session` (bare), `profile_service._wiki_get` / `trends_service.wiki_get` (manual 429 retry), and `article_service.get_session()` (urllib3 `Retry` adapter). These should be one client.

**`lru_cache` never invalidates.** A long-running process serves stale article analyses indefinitely.

**Regex HTML parsing** in `trends_service` breaks silently if Wikipedia restructures its portal pages.

### Scale and deployment

**Everything is recomputed per request.** No caching layer, so two users asking about the same editor pay the full cost twice.

**No pagination anywhere.** Every endpoint returns its complete result set.

**Latency is dominated by deliberate `time.sleep(0.25)` calls** between API batches. Correct for rate-limit etiquette, but it means geo resolution is inherently serial and slow.

**Placeholder `User-Agent` contact details** in `http_client.py` (`contact@example.com`, `github.com/your-org/...`) and `article_service.py`. [Wikimedia's API etiquette](https://www.mediawiki.org/wiki/API:Etiquette) expects a real contact — fix before any real volume.

**English Wikipedia is hardcoded** everywhere except Discover's sitelink logic. Non-English editors get their profile from enwiki only.

---

## Suggested priorities

| Priority | Item | Why |
|---|---|---|
| 1 | Weighted multi-place geo matching | Biggest remaining relevance win; the data already exists |
| 2 | Fix the effort/affinity scaling | Two scoring terms currently do nothing |
| 3 | Surface partial failures | Silent degradation is the hardest class of bug to diagnose here |
| 4 | Unify the three HTTP clients | Removes a whole category of inconsistency |
| 5 | Response caching | Makes everything else feel faster |
| 6 | Broaden `TOPIC_KW`, or replace it with ORES/category embeddings | Fixes the structural bias in topic detection |
