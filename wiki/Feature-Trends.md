# Feature: Trends

**Endpoint:** `GET /api/trends[?country=IN&wiki=mlwiki&langs=en]`
**Service:** `services/trends_service.py`
**UI:** Overview ("Read today, needs work" and "Today's news")

Answers: *what are readers near me reading right now that I could improve?*

---

## Sources

| Source | API | Notes |
|---|---|---|
| Readers in the editor's country | `metrics/pageviews/top-per-country/<a2>/all-access/<y>/<m>/<d>` | Filtered to the editor's Wikipedias (home + `langs` + en) |
| The editor's home wiki | `metrics/pageviews/top/<lang>.wikipedia/all-access/<y>/<m>/<d>` | The localized main page is excluded (from `meta=siteinfo`) |
| Headlines | enwiki `Portal:Current_events` (section 0) | List items with at least one article link; heading items are skipped |

Pageview data lags by a day or two, so the service tries the last three days in turn.

## Only articles that need work

Every trending article is read through `cirrusdoc`. Only those with a maintenance issue or a Growth suggestion are kept, each with its issue chips. The country list and the home-wiki list are interleaved, because a small wiki's numbers would otherwise be buried under enwiki's.

v1 showed the global enwiki top 30 to everyone. Two of its five sources (`Category:Ongoing_events`, recent deaths) were always empty, and the DYK item was template chrome ("DYK queues Clear Next queue…"). All three were removed.

Results are cached for 3 h per (country, wiki, languages).
