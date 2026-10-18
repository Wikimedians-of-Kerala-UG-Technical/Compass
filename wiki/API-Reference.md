# API Reference

Base URL in development: `http://127.0.0.1:5000`. The frontend reads it from `VITE_API_BASE`.

Endpoints are `GET` unless marked otherwise, need no login, and return JSON (UTF-8; non-Latin titles are not escaped). Every per-user endpoint accepts an optional `wiki` parameter (a dbname such as `mlwiki`). Without it, the backend uses the editor's **home wiki**, meaning the Wikipedia where they have the most edits.

## Endpoint index

| Endpoint | Purpose | Typical latency |
|---|---|---|
| [`/api/profile/<username>`](#apiprofileusername) | Editor profile on the home wiki | 10–30 s (then cached 6 h) |
| [`/api/tasks/<username>`](#apitasksusername) | Ranked tasks on the home wiki | 10–40 s |
| [`/api/geo/<username>`](#apigeousername) | Places the editor writes about, and their focus | 10–30 s |
| [`/api/revisit/<username>`](#apirevisitusername) | The editor's own articles that need attention | 5–15 s |
| [`/api/discover/<username>`](#apidiscoverusername) | Articles and sections to translate | 10–40 s |
| [`/api/contribute/<username>`](#apicontributeusername) | Commons and Wikidata tasks | 5–20 s |
| [`/api/trends`](#apitrends) | Most-read articles that need work, plus headlines | 5–15 s |
| [`/api/article/<title>/guide`](#apiarticletitleguide) | Paragraph-level analysis of one article | 2–8 s |
| [`/api/article/<title>/external-references`](#apiarticletitleexternal-references) | Citable sources with ready-to-paste templates | 5–20 s |
| [`/api/stats/<username>`](#apistatsusername) | Streak, last-30-day activity, readers reached | 2–5 s (cached 1 h) |
| [`POST /api/feedback`](#feedback) | Vote on a task card | instant |
| [`/api/feedback/<username>`](#feedback) | The editor's votes, after checking which articles they then edited | 1 s |
| [`/api/alerts/<username>/stream`](#apialertsusernamestream) | Live alerts (server-sent events) | stays open |
| [`/api/events…`](#events) | An Event Registration worklist, ranked for one editor | 1–30 s |
| `/api/health` | `{"ok": true}` for load balancers | instant |

The per-user endpoints share one cached profile. The first call pays for it and the others reuse it, so the dashboard's parallel requests don't fetch contributions several times.

## Error conventions

| Status | Meaning | Body |
|---|---|---|
| `200` | Success | The documented payload. `partial: true` means a sub-source failed and the result may be incomplete. |
| `400` | Malformed request (unknown feedback action, unrecognised event reference…) | `{"error": "…"}` |
| `404` | No such account, no edits on that wiki, unknown wiki or event, event without a worklist | `{"error": "…"}` |
| `429` | Over `COMPASS_RATE_LIMIT` | `{"error": "Too many requests…"}` and `Retry-After` |
| `500` | Upstream or internal failure | `{"error": "Something went wrong (error 1a2b3c4d)…", "errorId": "1a2b3c4d"}`. Details only in the server log, under that id |

Usernames are normalised the way MediaWiki does it (underscores → spaces, first letter capitalised), so `netha_Hussain` and `Netha Hussain` share one cached profile.

---

## `/api/profile/<username>`

Full detail: [[Feature-Editor-Profile]]

| Field | Type | Notes |
|---|---|---|
| `username` | string | Canonical spelling from Meta |
| `homeWiki`, `homeLang`, `homeUrl` | string | e.g. `mlwiki`, `ml`, `https://ml.wikipedia.org` |
| `wikis` | object[] | The editor's Wikipedias: `{dbname, lang, url, editcount}`, most edits first |
| `languages` | object[] | Babel (level ≥ 2 or N) plus wikis with ≥ 100 edits: `{lang, level, source, dbname, editcount, url}` |
| `total` | int | Global edit count across all Wikimedia wikis |
| `homeEdits` | int | Edit count on the home wiki |
| `sisterProjects` | object | `{wikidatawiki: n, commonswiki: n}` |
| `editsAnalysed` | int | Contributions read (max 2,000, newest first) |
| `uniqueArticles` | int | Distinct articles in those contributions |
| `topics` | object[] | ML topics over edited articles: `{path, slug, label, share}`, where `slug` is usable as `articletopic:` |
| `regions` | object[] | Region topics (e.g. South Asia), same shape |
| `countries` | object[] | `{name, a2, a3, qid, share}`; `a3` is usable as `articlecountry:` |
| `topTopics` | string[] | Labels of the top 3 topics (compatibility) |
| `topCategories` | object[] | `{name, count, size}`: visible categories the editor works in, minus tracking and huge ones |
| `editTypes` | object | Label → count, from change tags first and then edit summaries |
| `reverted` | object | `{count, of, share}`: article edits reverted by **someone else** (self-reverts excluded) |
| `heavilyEdited` | object[] | `{title, count, lastEdit}`, 3+ edits, max 15 |
| `createdArticles` | string[] | 50 most recent creations (`ucshow=new`) |
| `createdCount`, `createdCountCapped` | int, bool | Creations counted up to 1,000 |
| `recentEdits` | object[] | 15 newest, with home-wiki `diffUrl` and `articleUrl` |
| `secs` | number | Build time |

## `/api/tasks/<username>`

Full detail: [[Feature-Task-Recommendations]]

**Query parameters**

| Param | Meaning |
|---|---|
| `wiki` | Wiki to search (default: home wiki) |
| `lat`, `lon`, `place` | Optional. Adds a "near where you edit" source (`nearcoord:25km`). The frontend passes `geo.focus.local`. |

**Response**: `{wiki, mode, tasks[], scopes[], candidates, hidden?, partial, failed[], secs}`. `mode` is `guided` for editors with fewer than 200 edits on that wiki (Growth's link and image tasks only, plus a whole-wiki scope) and `standard` otherwise. Tasks the editor voted down, marked done or dismissed are left out; `hidden` counts them. Each task:

| Field | Notes |
|---|---|
| `title`, `wiki`, `url`, `editUrl` | |
| `type` | Primary issue: `add_refs`, `more_refs`, `add_citations`, `inline_cites`, `fix_orphan`, `dead_links`, `expand`, `update`, `add_link`, `add_image` |
| `issues` | Every issue found: `{key, label, since}`, where `since` = `YYYY-MM` from the dated tracking category |
| `meta` | `{label, effort, min}` |
| `reason`, `reasons` | Why it was picked for this editor, e.g. "In “Kerala cuisine”, where you edited 23 articles" |
| `details` | e.g. `["Start-class", "6 kB", "tagged since 2026-02", "53 views/day"]` |
| `scope` | Which source found it: `topic:…`, `cat:…`, `near`, `like:…`, `wiki` (guided mode) |
| `signals` | The six ranking components, each 0–1 |
| `score`, `pageviews`, `quality`, `size`, `topic`, `country`, `staleDays` | |

## `/api/geo/<username>`

Full detail: [[Feature-Geographic-Focus]]

`{wiki, articlesWithGeo, topPlaces[], topCountries[], focus: {region, local, country}}`. Each place is `{qid, name, nameEn, count, level, coord}`, where `level` is `country`, `admin1` or `local`. Labels are in the home wiki's language.

## `/api/revisit/<username>`

Full detail: [[Feature-Revisit]]

`{wiki, checked, tasks[]}`. Each item:

| Field | Notes |
|---|---|
| `title`, `url`, `editUrl`, `source` (`created`/`edited`), `editCount` | |
| `tags` | `{key, label, since, newSinceYourEdit}`. `check_edit` = latest edit by someone else has revert risk ≥ 0.9 |
| `yourLastEdit`, `lastEdit` | `lastEdit = {user, timestamp, revid, revertRisk}` |
| `hasNew`, `weak` | Sorted new-first, weak (stub or suggestion only) last |
| `quality`, `size`, `reason` | |

## `/api/discover/<username>`

Full detail: [[Feature-Discover]]

| Param | Meaning |
|---|---|
| `region`, `local` | Wikidata QIDs from `geo.focus`, for "missing near you" gaps |
| `regionName` | Display name |

`{monolingual, pairs[], languages[], articles[], sections[], regionGaps[], missingHere[]?, partial, secs}`.
- `missingHere` (monolingual editors on a non-English wiki only): widely linked English articles in their topics and country with no article on their wiki: `{title, qid, why, sourceUrl, localTitle, createUrl, wikidataUrl}`. `createUrl` opens the edit page for `localTitle`, the item's Wikidata label in their language, when it has one.
- `articles`: `{title, qid, source, target, languages, size, why, sourceUrl, translateUrl}`.
- `sections`: `{sourceTitle, targetTitle, missing: [{section, targetHeading, size, translateUrl}], targetUrl}`.
- `regionGaps`: `{qid, title, label, sitelinks, target, region, translateUrl, sourceUrl}`.
- `translateUrl` opens `Special:ContentTranslation` (with `sourcesection` for sections).

## `/api/contribute/<username>`

Full detail: [[Feature-Contribute]]

| Param | Meaning |
|---|---|
| `place`, `placeName` | Wikidata QID for the Wikidata gaps (the frontend sends `focus.local`, else `focus.region`) |

`{wiki, language, commons: {uploads, unused[]}, wikidata: {place, items[]}, events[], partial, failed[]}`.
- `unused`: `{file, thumb, url, coord, articles[], matchedBy}`.
- `items`: `{qid, label, sitelinks, missing: ['description', 'label'?], url}`.

## `/api/trends`

Full detail: [[Feature-Trends]]

| Param | Meaning |
|---|---|
| `country` | ISO alpha-2 (`IN`) for `top-per-country` |
| `wiki` | Home wiki for `top/<lang>.wikipedia` |
| `langs` | Extra language codes, comma-separated |

`{country, wiki, trending[], checked, droppedAsAutomated, news[]}`. Articles whose human traffic that day was more than 92% or less than 3% desktop are dropped as automated (`droppedAsAutomated` counts them). `trending` holds only articles with a maintenance tag or Growth suggestion: `{title, wiki, views, day, url, editUrl, issues[], quality, source}`.

## `/api/article/<title>/guide`

Full detail: [[Feature-Article-Guide]]. `?wiki=` defaults to `enwiki`. Titles can contain `/`.

`{title, wiki, url, editUrl, quality, qualityNext, importance, wikiprojects, topics, currentSize, totalRefs, hasInfobox, hasImages, sections[], inlineTags[], missingSections[], wikidata, citedUrls[], suggestions[], secs}`.
- Each section: `{id, name, level, chars, refCount, uncitedParagraphs[], inlineTags[]}`.
- Each suggestion: `{type, text, section?, url?, image?}`, where `type` is `refs`, `inline`, `banner`, `links`, `structure`, `media`, `section` or `facts`.

## `/api/article/<title>/external-references`

Full detail: [[Feature-Article-Guide]]

`{title, wiki, query, sourcesUsed[], medical, alreadyCitedSkipped, keysMissing[], results[], partial, failed[], secs}`. Each result: `{title, year, venue, authors, doi, pmid, isbn?, kind?, url, source, citations, cite}`, where `cite` is a ready-to-paste `{{cite journal|…}}`, `{{cite book|…}}` or `{{cite web|…}}`. Non-medical articles also search Open Library, Internet Archive and (with `GOOGLE_BOOKS_API_KEY`) Google Books; `keysMissing` lists the optional keys that aren't set.

The old `/api/article/<title>/references` endpoint was removed: it suggested other Wikipedia articles as sources, which Wikipedia doesn't allow (WP:CIRCULAR).

## `/api/stats/<username>`

Full detail: [[Feature-Stats-and-Feedback]]. `?wiki=` defaults to the home wiki.

`{username, wiki, streak: {current, longest90}, last30: {edits, articles, bytesAdded}, readers: {monthly, articlesChecked, articlesTotal, top[]}, calendar, compass, secs}`.
- `streak.current` counts consecutive UTC days with an edit, ending today or yesterday.
- `readers.monthly` = 30 days of human page views for up to 25 articles edited in the last 30 days.
- `calendar`: `{"YYYY-MM-DD": edits}` for the last 90 days.
- `compass`: `{up, down, done, dismiss, edited}` from task feedback.

## Feedback

Full detail: [[Feature-Stats-and-Feedback]]

`POST /api/feedback` with JSON `{username, wiki, title, action, type?, scope?, signals?, score?}`, where `action` is `up`, `down`, `done` or `dismiss`. Returns `201 {id, username, wiki, title, action}`. `signals` is the task's own `signals` object; only the six known keys are stored.

`GET /api/feedback/<username>?wiki=` first marks votes whose article the editor has edited since (within 60 days), then returns `{wiki, items: [{title, action, type, editedAt}], summary}`.

## `/api/alerts/<username>/stream`

Full detail: [[Feature-Live-Alerts]]. A `text/event-stream`. The first event is `ready` (`{watching, wiki}`); after that each `alert` event is one of:
- `{kind: "edit", title, wiki, user, comment, bot, timestamp, url, diffUrl}`: someone else edited one of the editor's articles.
- `{kind: "tagged" | "untagged", title, wiki, issue, label, user, timestamp, url}`: an article was added to or removed from a tracking category.

A `: keepalive` comment is sent every 25 s. Not rate-limited.

## Events

Full detail: [[Feature-Events]]

| Request | Params | Returns |
|---|---|---|
| `GET /api/events/resolve` | `ref`: an event ID, a `Special:EventDetails` link or an `Event:` page | `{id}` (`400` for anything else) |
| `GET /api/events/<id>` | | `{id, name, status, starts, ends, timezone, wikis[], topics[], goal, tracksContributions, eventPage, eventPageUrl, detailsUrl, worklist: {dbname: [titles]}, participants[]}` |
| `GET /api/events/<id>/rank/<username>` | `wiki` (optional) | `{event, username, wiki, wikis: {dbname: count}, profileWiki, items[], toCreate[], total, secs}`. Each item: `{title, wiki, url, editUrl, needs[], meta, reasons[], details[], signals, score}` |
