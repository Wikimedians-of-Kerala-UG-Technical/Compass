# Compass — Hands-on Evaluation (October 2026)

> **How this was done, and how to redo it:** see [`eval/README.md`](eval/README.md) for the step-by-step playbook, scripts and scoring rubric. The computed metrics for this run are in [`eval/baseline/2026-10-13-metrics.json`](eval/baseline/2026-10-13-metrics.json).
>
> **Update:** Sections 1–6 evaluate the original code (v1, commit `151efa4`). After the rewrite, the same evaluation was re-run. See [§7](#7-re-evaluation-after-the-rewrite-v2): the overall score went from **3.5 to 7.5**.

> **Question:** Does Compass give a Wikimedia editor something they can actually *act on*?
>
> **Method:** I ran the backend locally at commit `151efa4`. For each of 15 real editors I followed the exact sequence the frontend runs (`appStore.start()`: profile → tasks → revisit → geo → re-ranked tasks → discover). I saved every response and timed each call. I then checked claims against live Wikipedia and Wikidata and judged whether each recommendation was something that editor would plausibly pick up. Everything was read-only; no edits were made anywhere.
>
> **Short answer:** **Revisit** works, and **Discover** has a genuinely valuable core. **Tasks**, the headline feature, mostly returns keyword noise: the same handful of articles for everyone, matched by words in article *titles*. There is also a structural problem. Compass reads **only English Wikipedia**, so for the three Kerala editors you named it sees a small fraction of what they actually do.

---

## 1. Who I tested

Edit counts come from `meta=globaluserinfo`.

| Editor | Global edits | Where they actually work | enwiki share | Why included |
|---|---:|---|---:|---|
| **Ranjithsiji** | 429,502 | Wikidata 295k · Commons 98k · **mlwiki 26k** · enwiki 3.3k | 0.8% | Requested |
| **Netha Hussain** | 251,719 | Wikidata 132k · Commons 75k · ml-wiktionary 20k · enwiki 14k · mlwiki 6k | 5.5% | Requested |
| **Athulvis** | 238,531 | Wikidata 222k · Commons 15k · mlwiki 104 · **enwiki 46** | 0.02% | Requested |
| Satdeep Gill | 67,937 | **pawiki** 20k · Commons · Wikidata · pa-wikisource | 5.5% | India / Punjabi |
| Ravidreams | 38,841 | **tawiki** 29k · ta-wiktionary | 1.0% | India / Tamil |
| Titodutta | 313,457 | **enwiki 158k** · Wikidata · Commons · bnwiki | 50% | India / enwiki-centric |
| Olaniyan Olushola | 12,968 | Wikidata · enwiki · Commons · yowiki | 28% | Nigeria |
| Bobbyshabangu | 11,161 | enwiki · Commons · **sswiki** · nrwiki · zuwiki | 29% | South Africa |
| Ainali | 263,800 | Wikidata 170k · Commons · **svwiki** 28k | <1% | Sweden |
| Doc James | 2,073,437 | Commons 1.7M · **enwiki 315k** (medicine) | 15% | Global, medicine |
| Rosiestep | 557,431 | **enwiki 330k** (Women in Red) · Commons | 59% | Global, biographies |
| Hog Farm | 61,888 | **enwiki 61k** (American Civil War, FA writer) | 98% | Niche enwiki specialist |
| Cwmhiraeth | 139,937 | **enwiki 139k** (marine invertebrates, zoology) | 99% | Niche enwiki specialist |
| Newcomer A | 255 | enwiki, registered Sep 2026 | 100% | New editor via Growth tasks |
| Newcomer B | 136 | enwiki, registered Sep 2026 | 100% | New editor via Growth tasks |

The two newcomers were chosen from recent `newcomer task`-tagged edits. They're anonymised here because they're new volunteers, not public figures.

**Finding zero, before any feature runs:** 8 of 15 editors, including all three you named, do most of their work outside English Wikipedia. Every Compass feature except Discover reads only `en.wikipedia.org`. For Athulvis, Compass built a "high quality" profile from **46 edits** while 238,485 others went unseen.

---

## 2. Scorecard

| Feature | Endpoint | Score | One-line verdict |
|---|---|:-:|---|
| Revisit | `/api/revisit` | **7/10** | Accurate and genuinely personal. The best thing in the product. |
| Discover | `/api/discover` | **5/10** | Right idea (cross-language gaps) and correct data, but badly ranked and unusable by monolingual editors. |
| Geographic focus (data) | `/api/geo` | **5/10** | Resolves real place hierarchies well; the way the frontend *picks* a focus is broken. |
| Editor profile | `/api/profile` | **3/10** | enwiki-only. Topics come from a 12-word list, quality tier is inverted, slow. |
| Article guide | `/api/article/…/guide` | **3/10** | Generic section templates. False "very short section" alarms on featured-quality articles. |
| External references | `/api/article/…/external-references` | **3/10** | Real papers sometimes, but Semantic Scholar is 100% rate-limited and title-only queries pull junk. |
| Recommended tasks | `/api/tasks` | **2/10** | Keyword matches on article titles; near-identical feed for everyone. |
| Trends / news | `/api/trends` | **2/10** | Not personalised. 2 of 5 sources silently empty, and the first DYK item is admin junk. |
| "Wikipedia references" | `/api/article/…/references` | **1/10** | Recommends Wikipedia articles as citations, which Wikipedia itself forbids (WP:CIRCULAR). |
| Speed and reliability | — | **3/10** | 1–3 minutes to a full dashboard for active editors. Failures are silent. |

Scores use the five-dimension rubric in [`eval/README.md` §4](eval/README.md#4-rating-rubric) (relevance, actionability, correctness, coverage, performance; 0–2 each). The per-dimension breakdown is in the calibration table there.

**Overall: 3.5/10 today** (mean of the rows above, 3.4, rounded to the nearest 0.5). The pieces that score well (Revisit, Discover, Geo data) show that a 7–8/10 tool is within reach. Section 5 explains how.

---

## 3. Feature-by-feature

### 3.1 Recommended Tasks: 2/10

**How it works** (`backend/routes/tasks.py:31`): for each of the user's top 3 topic words plus one place name, it runs a full-text search like `hastemplate:"Unreferenced" biography` and takes 4 hits.

**What came back:**

| Editor | Actual niche | Compass's top recommendations |
|---|---|---|
| Netha Hussain | Physician; radiology, women in medicine, Kerala | *Orlando: A Biography* (Virginia Woolf novel), *Dictionary of National Biography*, *James Bond: The Authorized Biography of 007*. Medicine tasks rank **#40–51 of 51**: "Doctor of Medicine", "Hospital medicine". |
| Doc James | Medicine (WikiProject Medicine lead) | "Doctor of Medicine", "MBBS", then **"Kentucky Wildcats football"**, because 2 of his 2,633 articles resolved to Kentucky. |
| Hog Farm | American Civil War featured articles | *Orlando: A Biography*, **Arkansas Department of Corrections**, Arkansas Delta |
| Cwmhiraeth | Marine invertebrates, zoology | *Orlando: A Biography*, then **Russian Empire** military history |
| Rosiestep | Women in Red, biographies of women | *Identical* list to Cwmhiraeth: *Orlando*, Russian Empire divisions |
| Ainali | Swedish topics, open knowledge | Stockholm, then **"Orange County Water District"** (matched the word "County") |
| Newcomer A | Small edits on varied pages | "Geography", "England, England" (a novel), England national football team |
| Ranjithsiji / Netha / Athulvis | Three different Kerala editors | **The same 8 Kerala articles** ("Kerala", "Economy of Kerala", "Education in Kerala", …) |

**Measured across all 15 editors:**
- *Orlando: A Biography* and *Dictionary of National Biography* appear in the **top 10 for 9 of 15 editors**.
- For **9 of 15 editors, all 10 top tasks literally contain the topic or place word in their title**. The feed matches words, not subjects.
- **5–8 of every editor's top 10 show `pageviews: 0`.** Example: "Kerala" is shown as 0 views/day; the real figure is 3,167/day. Cause: `score_and_rank` picks which tasks to look up *before* the geo bonus is added (`scoring_service.py:104`), so geo tasks jump to the top without ever being looked up.
- Recommended articles are often huge, heavily watched pages ("Kerala" is 313 kB with 676 refs). "Add citations to *Kerala*" is not a 10-minute task, and it's a poor first task for a newcomer.
- A task card says only "Has [citation needed] tags — india". It doesn't say how many tags, which section, how old they are, or **why this task is for you**.

**What's good:** the maintenance templates are real and live, so everything recommended does need work, and the feed is stable (49–50/50 overlap across three reruns).

**Root causes:**
1. Topic words are used as search terms (`tasks.py:35`), so the matches are lexical.
2. Topics come from a hard-coded 12-entry keyword list (`profile_service.py:8`). Cwmhiraeth's marine-biology categories ("Gastropods described in 1832") match no keyword, so she becomes "biography / culture / history".
3. The place name is also just a keyword ("Stockholm County" matches *Orange County*).

**Proof the fix is cheap.** Compass's own Discover endpoint already computes each user's real categories. Feeding those into CirrusSearch instead of keywords:

| Query | Hits | Top results |
|---|---:|---|
| `hastemplate:"Citation needed" medicine` *(current)* | 39,794 | Alternative medicine, Traditional medicine, Sports medicine |
| `hastemplate:"Citation needed" incategory:"20th-century Indian medical doctors"` | 95 | Muthulakshmi Reddy, Abhay and Rani Bang, Tehemton Erach Udwadia |
| `hastemplate:"More citations needed" incategory:"Male actors in Malayalam cinema"` | 31 | Nedumudi Venu, Innocent (actor), Sathyan |
| `hastemplate:"Citation needed" incategory:"Kerala cuisine"` | 7 | Dosa, Matta rice, Pidiyum kozhiyum |
| `hastemplate:"More citations needed" deepcat:"Radiologic signs"` | 2 | Perkin's line, Fogging phenomenon |
| `hastemplate:"Citation needed" articletopic:medicine-and-health` | 15,835 | Malnutrition, Plague, ALS |
| `hastemplate:"More citations needed" nearcoord:40km,9.97,76.28` (Kochi) | 196 | Angamaly, Thrippunithura, Perumbavoor |

Every one of these is something the named editor would recognise as "mine". `articletopic:` (Wikimedia's ML topic model) also works on **mlwiki**: `hastemplate:"Unreferenced" articletopic:films` returns 101 Malayalam film articles.

---

### 3.2 Revisit: 7/10 ✅

**How it works** (`watchlist_service.py`): it takes the articles a user has edited heavily or created, then flags those that carry maintenance tracking categories.

**What came back:** 132 items across 15 editors. I checked the tags on a sample against live categories and **all were accurate**. Examples:
- Netha Hussain: *Erachichor* (her article) is unreferenced, orphaned and a stub; *Idli podi* is unreferenced.
- Ranjithsiji: *Koomapatti* has citation-needed tags, needs more references, and is a stub.
- Bobbyshabangu: 20 items, e.g. *Nana Sita* is unreferenced and orphaned.

This is the only feature where every item is relevant by construction, and editors care about articles they wrote.

**Problems:**
- **Tags are mislabelled.** "Articles needing *additional* references" is shown as **"Unreferenced"**, which is a different and much stronger tag. SARS-CoV-2 (a 130 kB article) is displayed as "Unreferenced".
- **"Since you last worked on them" is never checked.** The tag date (e.g. *Pekan, Pahang*, tagged September 2010) isn't compared with the user's last edit. Newly broken articles and decade-old tags look identical.
- **36% of items (47/132) are only "Stub" or "Could be expanded"** (any article under 4 kB). That's weak signal, and these rank alongside real problems.
- **Article creations are detected by edit summary** (`classify_edit` looks for "creat"). Netha Hussain has **648** real enwiki creations (`ucshow=new`); Compass found 20, capped at 20. Hog Farm has 663 and Compass found 20. Athulvis has 3 and Compass found 0. Ravidreams has 2 and Compass found 0.
- Newcomers get nothing (Newcomer B: 0 items), and there's no fallback.
- It's enwiki-only, so Ranjithsiji's 26k mlwiki edits produce no Revisit items.

---

### 3.3 Discover: 5/10 (best idea, weakest execution)

**How it works** (`routes/discover.py`): it takes the user's top categories, samples 30 members of each, and reports which ones are **missing on the other Wikipedias the user edits**.

**The core is valuable and the data is correct.** I verified on Wikidata that *K. T. C. Abdullah* (Q64781741), *V. C. Abhilash* and *Aaryan Krishna Menon* really have no Malayalam article. For a Malayalam editor, "Malayalam film people who exist in English but not Malayalam" is a perfect, ready-made worklist. The same goes for Yoruba (Olaniyan) and siSwati, isiZulu and the other South African languages (Bobbyshabangu).

**Problems:**
- **Monolingual editors get nothing.** Hog Farm, Cwmhiraeth and both newcomers each received **0 suggestions**. Most enwiki editors are monolingual.
- **"Known languages" is inflated.** It's any Wikipedia with 10 or more edits, so it includes interwiki fixes, bot-like edits and test wikis:
  - Doc James: **77 languages**, so every suggestion is "missing in 75 wikis".
  - Ainali: 46 languages, including `abstractwiki` and `testwiki`.
  - Titodutta: 28 languages, including `testwiki`.
  - The regex `^https://([a-z0-9-]+)\.wikipedia\.org$` matches `test.wikipedia.org` and `test2.wikipedia.org`.
- **Suggestions are alphabetical, not ranked.** `categorymembers` returns members A→Z, and only the first 30 are taken. Every list starts with "Aaryan…", "Abbas…", "Abelson murine leukemia virus…". Nothing is weighted by importance, pageviews or how many languages already cover the article.
- **Wrong category signal for light users.** With only 45 enwiki edits, Athulvis's category counts all tie at 1, and the top category becomes *11th-century inscriptions*. He is told to translate **Swedish runestones**.
- **The action link is wrong.** "Create in mlwiki" opens `ml.wikipedia.org/wiki/<English title>` (`DiscoverView.vue:42`). That would create a Malayalam page under an English title. It should open Content Translation: `ml.wikipedia.org/wiki/Special:ContentTranslation?page=<title>&from=en&to=ml`.
- It takes 40–195 seconds.

---

### 3.4 Geographic focus: data 5/10, usage 2/10

**The `/api/geo` data is genuinely good.** Walking Wikidata P131 chains gives:
- Nigeria → Lagos State → Lagos
- South Africa → Gauteng → City of Johannesburg
- India → Kerala → Ernakulam district → Kochi
- India → Punjab → Jalandhar division

**How the frontend uses it is broken** (`appStore.js:geoFocusName`). It picks the *first place that isn't one of the top-3 countries*, ignoring counts:
- **Titodutta**: India 86, but focus = **Kamikawa Subprefecture, Hokkaido** (10 articles). Result: tasks on Japanese train stations.
- **Rosiestep and Cwmhiraeth**: focus = **Russian Empire**. It's a historical state that isn't among their top-3 countries, so it counts as a "region". It comes from birthplaces in historical biographies.
- **Doc James**: focus = **Kentucky** (2 articles out of 2,633).
- **Netha Hussain**: "Kingdom of Great Britain" ×69. Birthplace chains pick `claims[0]` rather than the preferred or current statement, and land on dissolved states.
- **Athulvis**: "Kerala Soil Museum" is listed as a *place*, because the article itself is used as the starting point and its own label gets counted.

The geo bonus (+0.4) then pushes these place-name keyword matches above everything else.

---

### 3.5 Editor Profile: 3/10

- **enwiki only**: Athulvis's profile is built from 46 of 238k edits. Ravidreams is profiled from 180 enwiki pages, not his 29k Tamil edits.
- **Topics**: the 12-keyword list (`TOPIC_KW`) is skewed. "india" is a topic; Nigeria, Sweden and Japan are not, and zoology maps to nothing. Only 50 random articles are sampled.
- **Quality tier is inverted.** Doc James and Cwmhiraeth are rated **"developing"**. Both are among enwiki's most experienced editors, and they revert a lot of vandalism. The metric is "share of *your* edits that are reverts", which punishes patrollers.
- **"Total edits"** shows the global count (e.g. 429,502), but everything else describes the enwiki slice. The two numbers sit side by side and contradict each other.
- **Edit types depend on edit summaries.** "minor" and "general" make up most edits for every user.
- **Slow.** Up to 20,000 contributions are fetched in 40 sequential calls, but only 50 articles are used for topics:
  - Doc James: 137 s
  - Hog Farm: 115 s
  - Rosiestep: 109 s
  - Titodutta: 101 s

  The whole dashboard is blocked behind this call.

---

### 3.6 Article Guide: 3/10

Tested on: Kerala Sahitya Akademi, Erachichor, Lake Louise criteria, Anesthesia for eye surgery, Koomapatti, Tuberculosis.

- Suggestions are fixed templates by article type ("Add 'History' section", "Add 'Description' section", "Add an infobox", "Add images from Wikimedia Commons"). They appear on nearly every article, whether or not they make sense.
- **False alarms on high-quality articles.** On *Tuberculosis* (180 kB, 380 refs) it says *"Expand 'Causes' — very short (2 chars)"*. The section splitter counts only the text before the first subsection.
- Medical detection depends on keyword substrings in category names, so it is fragile.
- "Add images from Wikimedia Commons" never offers an image. Compass could look up the Wikidata P18 image or Commons category, which is where Ranjithsiji and Netha Hussain contribute most.
- One run on *Kerala Sahitya Akademi* returned "Wikipedia API failure". The 5 s `httpx` timeout fails under load, and the UI shows no retry.
- The good part: the per-section reference counts are real, and "Add refs to 'History' — no citations" is a concrete, useful hint.

### 3.7 References: Wikipedia list 1/10, external list 3/10

- **`/references` returns other Wikipedia articles** with fake metadata (`"authors": "Wikipedia Contributors"`). Wikipedia can't cite itself (WP:CIRCULAR). For *Lake Louise criteria* it suggested *Banff National Park* and *Princess Stéphanie of Belgium*. This list should be removed or renamed "related articles".
- **External references:**
  - **Semantic Scholar returned HTTP 429 on 100% of calls** (no API key), and the code silently drops it.
  - **CrossRef title-only queries pull noise.** For *Lake Louise criteria* you get "NEUTRINOS AT LAKE LOUISE" and "Lake-Tack, Dame Louise, GCMG" next to the correct myocarditis papers.
  - **PubMed is triggered only if the *title* contains a medical keyword.** *Tuberculosis* and *Lake Louise criteria* got no PubMed results.
  - **Results aren't citable as-is**: no authors, year, journal or ready-to-paste `{{cite journal}}`, and no check for whether the article already cites a paper.

### 3.8 Trends: 2/10

- It's the same for everyone and has no connection to the user's topics or region.
- `Category:Ongoing_events` **doesn't exist** and `Recent_deaths` returned nothing, so 2 of 5 sources are silently empty.
- The first "Did you know" item is template chrome: *"DYK queues Clear Next queue update edit history purge…"*.
- Trending articles don't say what work they need. Most top-viewed articles are already heavily edited, so they're the least useful place to send a volunteer.

### 3.9 Speed and reliability: 3/10

| Step (median across 15 editors) | Time |
|---|---:|
| Profile, which blocks the UI | 16 s (max 137 s) |
| Geo | 76 s (max 150 s) |
| Discover | 95 s (max 195 s) |
| Tasks, re-ranked with geo | 14 s |

Notes:
- 4 editors ran concurrently, which roughly matches a small workshop.
- Every external failure becomes an empty list (bare `except`), so the UI can't tell "nothing to do" from "a source failed".
- `debug=True`, the hard-coded API base URL and a placeholder User-Agent (`your-org/wikitask-pro`) are still in place. Wikimedia's User-Agent policy requires real contact information.

---

## 4. What's genuinely good

1. **The premise is right.** "Look at what I already do, then tell me what to do next" is exactly what editors lack. Existing tools are either generic, like Growth Suggested Edits, or narrow, like Citation Hunt.
2. **Revisit is accurate and personal.** "Your own article picked up a tag" is the highest-intent task there is.
3. **Discover's cross-language gap detection is technically correct** and is the best answer the tool has for Indic and African-language editors.
4. **The Wikidata place-hierarchy resolver** (`geo_service.py`) is solid engineering and reusable.
5. **The codebase is small, readable and honest about itself.** `wiki/Known-Issues-and-Limitations.md` predicted half of what I found. The fixes below are mostly re-plumbing, not rewrites.

---

## 5. How to make Compass worth an editor's time

### Priority 0: stop recommending noise (days of work)

| # | Change | Where |
|---|---|---|
| 1 | **Use the user's real categories, not topic words, as the search scope.** Run `hastemplate:X incategory:"<user's top category>"` (or `deepcat:`) over the categories Discover already computes; add `articletopic:` as a broad fallback. Drop `TOPIC_KW` and `GENERIC_TOPICS`. | `tasks.py`, reuse `discover.py` category logic |
| 2 | **Use real geography.** Search by coordinates (`nearcoord:<radius>,<lat>,<lon>` of the user's top place) instead of the place-name string. Weight places by count, and drop dissolved states (Wikidata P576) and places under ~5% of geo-tagged edits. | `geoFocusName`, `tasks.py`, `geo_service.py` |
| 3 | **Look up pageviews and staleness for the *final* top N**, after all bonuses, so no task shows `pageviews: 0` by accident. | `scoring_service.py:104` |
| 4 | **Prefer small, tractable articles.** Filter by page length and maintenance-tag age, and show *how many* `{{cn}}` tags and *which section*. Never recommend a 300 kB article as a quick task. | `tasks.py`, task card |
| 5 | **Say why each task is for this user**: "Because you edited *Kayadu Lohar* and 12 other Malayalam film articles". | task payload + `TasksView.vue` |
| 6 | **Fix the mislabelled tags.** "Needs more references" ≠ "Unreferenced". Show the tag date and flag "new since your last edit". | `watchlist_service.py` |
| 7 | **Detect created articles with `ucshow=new`**, not edit-summary guessing, and lift the 20 cap. | `profile_service.py` |
| 8 | **Remove the "Wikipedia references" list** (or relabel it "Related articles"). Get a Semantic Scholar key or drop that source. Trigger PubMed on article categories, not title words. Output ready-to-paste `{{cite journal}}`. | `article_service.py` |
| 9 | **Fix the Discover link** to go through Content Translation (`Special:ContentTranslation?page=…&from=en&to=ml`). | `DiscoverView.vue:42` |
| 10 | **Remove `qualityTier`** or replace it with "share of your edits reverted *by others*". | `profile_service.py` |

### Priority 1: make it multi-wiki, which is the change that matters for your community

The editors you care about live on **mlwiki, Wikidata and Commons**. Compass should too.

1. **Detect the user's home wiki.** Use the content wiki with the most edits from `globaluserinfo`, plus their declared languages from `meta=babel` (e.g. Ranjithsiji: `ml-N, en-3, hi-1`). Ignore `test*`, `abstractwiki` and any wiki with fewer than about 100 edits.
2. **Build the profile and tasks on that wiki.** Every API Compass uses (usercontribs, categories, CirrusSearch `hastemplate`, `articletopic:`, `nearcoord:`) works on mlwiki. Resolve maintenance template names per wiki through their Wikidata items instead of hard-coding English names.
3. **Make Discover rank, not list.** Order by source-wiki pageviews and the number of languages that already cover the article. Restrict "missing in" to the user's real languages, and **include English as a source for monolingual editors**, e.g. "these redlinks in your area have an article in French or German".
4. **Add tasks for Commons and Wikidata contributors.** Examples:
   - "Articles near Kochi with no image": `nearcoord:` plus a no-file filter returns 15 for Kochi today. Ranjithsiji is actively photographing Kochi.
   - "Wikidata items you created that have no Malayalam label."
   - "Your Commons photos not used in any article."

   These are the highest-value tasks Compass could offer its own community, and none of them exist today.

### Priority 2: become the tool editors open every week

- **Newcomer mode.** For editors with under ~500 edits, show small articles only and link to their Growth "Suggested edits" homepage rather than competing with it.
- **Campaign awareness.** Surface relevant WikiProjects, Women in Red redlists and active campaigns or edit-a-thons that match the user's categories or region.
- **A feedback loop.** Record which recommendations were opened, then check the user's contributions later to see whether they edited that page. Use the result to tune ranking, and report it ("you fixed 6 of 10 suggestions this month").
- **Speed.**
  - Fetch about 2,000 contributions instead of 20,000; topics don't need more.
  - Cache per user, with expiry, so repeat visits are near-instant.
  - Show a partial dashboard immediately.
  - Report failed sources (`partial: true`) instead of returning empty lists.
- **Hygiene.** Set a real User-Agent, use config-driven API URLs, turn off `debug`, and consolidate the three HTTP clients.

### Where Compass should position itself

| Existing tool | What it does | What Compass can do that it can't |
|---|---|---|
| Growth "Suggested edits" | Topic-filtered tasks for newcomers on many wikis | Use the editor's *own* footprint: their articles, categories, places |
| SuggestBot | Article suggestions from edit history (enwiki, opt-in, posted to talk pages) | Work across wikis and live, with a reason and a guide for each task |
| Citation Hunt | Random `{{cn}}` snippets by category | Personal scope plus Revisit |
| Content Translation suggestions | "Translate articles similar to ones you translated" | Gaps across languages *the user actually speaks*, ranked by importance |

The defensible niche is **"your own footprint, across every wiki you touch"**: Revisit, Discover and category-scoped tasks. The generic maintenance feed is a commodity, and it's the weakest part of Compass today.

---

## 6. Reproducing this evaluation

Everything needed to rerun this evaluation is in [`eval/`](eval/):

- [`eval/README.md`](eval/README.md): the step-by-step procedure, metric definitions, the scoring rubric with this run's calibration breakdown, a regression checklist, and the report template.
- [`eval/cohort.md`](eval/cohort.md): the 13 core users, the segments they cover, and how to pick fresh newcomers.
- Scripts:
  - `harness.py` replays the frontend's calls.
  - `articles.py` tests the Guide and References endpoints.
  - `ground_truth.py` measures what each user really does.
  - `verify.py` spot-checks claims against live wikis.
  - `digest.py` prints a readable per-user dump.
  - `metrics.py` computes the cohort metrics.
- [`eval/baseline/2026-10-13-metrics.json`](eval/baseline/2026-10-13-metrics.json): this run's numbers, to compare future runs against.

Evaluated commit: `151efa4`. Date of run: 2026-10-13. Live wiki content changes, so exact titles will drift, but the patterns above come from the code and will reproduce.

---

## 7. Re-evaluation after the rewrite (v2)

Every Priority 0 and Priority 1 item in §5 was implemented, plus most of the redesign in [`WIKIMEDIA-RESEARCH.md`](WIKIMEDIA-RESEARCH.md) §8. The exceptions are listed under "Not built yet" below. The playbook was then re-run on the same 13 core editors and 2 freshly picked newcomers. The harness was updated to mirror the new frontend sequence: profile → trends → revisit → tasks → geo → tasks near the focus place → discover → Commons & Wikidata. Raw outputs are git-ignored; the metrics are in [`eval/baseline/2026-10-13-v2-metrics.json`](eval/baseline/2026-10-13-v2-metrics.json).

> **Caveat:** the same agent that built v2 also scored it. The automated metrics are objective. The relevance labels and rubric scores below are judgement calls. An independent re-run of `eval/` (another person or agent) is the honest next step.

### Before and after

| Measure | v1 | v2 |
|---|---|---|
| Profile built on the editor's home wiki | enwiki for everyone (8 of 15 actually work elsewhere) | Home Wikipedia per editor: ml ×2, ta, pa, sv, en ×10 |
| Users whose entire top 10 is title-keyword matches | 9 of 15 | **0** |
| Titles in ≥ 3 users' top 10 | 8 (*Orlando: A Biography* ×9, *Dictionary of National Biography* ×9, …) | **0** |
| Top-10 tasks showing 0 pageviews | 5–8 per user | 6 in total. All are real near-zero-traffic articles on ml/pa/sv; pageviews are now fetched after ranking. |
| Top-10 tasks found through the editor's own categories, articles or place | — | **7.5 of 10** on average |
| Top-10 tasks on articles over 100 kB | common (*Kerala*, 313 kB) | 3 across all 15 users |
| Relevance of top 10 (R / P / N, judged) | — | **111 R / 29 P / 10 N** of 150 (74% R) |
| Creations detected (Netha Hussain, Hog Farm) | 20, 20 | **648, 663** (exact, `ucshow=new`) |
| Quality signal for Doc James and Cwmhiraeth | "developing" (own reverts) | Reverted by others: 0.8% and 4.8% |
| Geo focus | Wrong for 5 of 15 (Kentucky, Hokkaido, Russian Empire ×2) | Count-based. Kerala/Ernakulam, Tamil Nadu/Sivaganga, Punjab/Amritsar, Lagos State/Lagos, Gauteng/Johannesburg, Stockholm, Odisha/Bhubaneswar. **None** for Doc James (9 geo articles of 512), which is correct. |
| Discover languages | Any wiki with ≥ 10 edits (up to 77) | Babel first, at most 3 pairs |
| Discover suggestions | Alphabetical category samples; link created a page under the English title | CX recommender, 48–60 articles + 12–30 missing sections per bilingual editor, each opening Content Translation |
| Discover for monolingual editors | Silently empty (4) | Still empty (4), but the UI explains why and how to enable it |
| Revisit items | 132 | 326 (exact creations, multi-wiki, dated tags, revert-risk check) |
| Revisit "weak only" share | 0.36 | 0.42. Growth "suggested links" now counts as weak. Weak items are sorted last. |
| Commons & Wikidata tasks | none | 20 unused photos and 20 Wikidata gaps for most editors |
| Latency p50 / max: profile | 16 s / 137 s | **10.7 s / 24 s** |
| Latency p50 / max: geo | 76 s / 150 s | 24 s / 46 s |
| Latency p50 / max: discover | 95 s / 195 s | **6.6 s / 9.4 s** |
| Latency p50 / max: tasks (with place) | 14 s / 52 s | 5.7 s / 26 s |
| Non-200 responses | 0 | 0 (after fixing a pageviews rate-limit crash found during this run) |

Relevance labels follow `eval/README.md` Step 8, for each editor's top 10:

| Editor | R | P | N | What they got |
|---|--:|--:|--:|---|
| Ranjithsiji (mlwiki) | 10 | 0 | 0 | Small Malayalam actress and film articles in categories he edits; "Ernakulam district" focus |
| Netha Hussain | 7 | 3 | 0 | Kerala cuisine, Kerala women, articles like *Feminism in Kerala* |
| Athulvis (mlwiki) | 7 | 3 | 0 | Palakkad villages needing links/images (Growth tasks), near the Nelliyampathy articles he edits |
| Satdeep Gill (pawiki) | 9 | 1 | 0 | Punjabi poets and writers |
| Ravidreams (tawiki) | 9 | 1 | 0 | Tamil film people and Tamil Nadu politicians |
| Titodutta | 9 | 1 | 0 | Current Indian films needing expansion |
| Olaniyan Olushola | 9 | 1 | 0 | University of Lagos alumni, Nigerian biographies |
| Bobbyshabangu | 10 | 0 | 0 | South African anti-apartheid activists, Zulu people |
| Ainali (svwiki) | 5 | 5 | 0 | Unreferenced Stockholm articles near him; climate-adjacent biographies |
| Doc James | 10 | 0 | 0 | Tropical and vaccine-preventable diseases, articles like his outbreak articles |
| Rosiestep | 8 | 2 | 0 | Woman's Christian Temperance Union women, 19th-century women writers |
| Hog Farm | 9 | 1 | 0 | Union victories of the Civil War, Union navy ships |
| Cwmhiraeth | 2 | 4 | 4 | Mostly pop-culture articles from her recent broad editing; only *Calluna* matches her botany |
| Newcomer A | 1 | 4 | 5 | Generic biographies (93 edits, mostly current events) |
| Newcomer B | 6 | 3 | 1 | K-pop and Greenland articles like theirs |

### Article Guide and Sources (same 7 articles as v1, plus one on mlwiki)
- *Tuberculosis*: no false "2 chars" alarm. It reports 2 dated dead links in citations. Sources are 7 PubMed reviews + 1 OpenAlex, every one with a `{{cite journal}}`.
- *Koomapatti*: points to the uncited lead sentence (`{{cn}}` since July 2026) and both banner tags with dates. No off-topic papers.
- *Lake Louise criteria*: no medical word in the title, but its ML topic routes it to PubMed. It gets myocarditis reviews and the 2018 criteria papers.
- *Kerala Sahitya Akademi*: quotes the two uncited paragraphs. Sources are mixed: a few relevant, some off-topic (Kerala literature in general).
- *നെടുമുടി വേണു* (mlwiki): the uncited paragraph in ജീവിതരേഖ, plus "Add ആദ്യകാല ജീവിതം (Early life)" and "അഭിനയ ജീവിതം (Filmography)", which exist in English and link to Content Translation.

### Scorecard (v2)

Dimensions are scored first and then summed, per `eval/README.md` §4. Perf is 1 when p50 is 5–30 s.

| Feature | Rel | Act | Corr | Cov | Perf | **v2** | v1 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Editor profile | 1.5 | 2 | 2 | 2 | 1 | **8.5** | 3 |
| Article guide | 1.5 | 2 | 1.5 | 1.5 | 2 | **8.5** | 3 |
| Revisit | 2 | 2 | 1.5 | 1.5 | 1 | **8** | 7 |
| Sources (external references) | 1.5 | 2 | 1.5 | 1 | 2 | **8** | 3 |
| Recommended tasks | 1.5 | 2 | 1.5 | 1.5 | 1 | **7.5** | 2 |
| Commons & Wikidata (new) | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 | **7.5** | — |
| Discover | 1.5 | 2 | 1.5 | 1 | 1 | **7** | 5 |
| Geographic focus | 1.5 | 1.5 | 1.5 | 1.5 | 1 | **7** | 5 |
| Trends | 1 | 1.5 | 1 | 1.5 | 2 | **7** | 2 |
| "Wikipedia references" | — | — | — | — | — | removed | 1 |
| Speed and reliability | | | | | | **6** | 3 |
| **Overall** | | | | | | **7.5** | 3.5 |

The overall score is the mean of the 10 rows: 75 ÷ 10 = 7.5.

### What still falls short
- **Editors with broad recent activity.** Cwmhiraeth's last 2,000 edits span pop culture and sport as well as botany, so her topic vector is diluted (2 R of 10). A longer window, or weighting by bytes added instead of edit count, would help.
- **Newcomers with little history** still get fairly generic tasks. A dedicated newcomer path (Growth tasks only, matched to the topics they chose on `Special:Homepage`) would be better.
- **Trends** take `top-per-country` as it comes, including traffic anomalies (*.xxx* and *XXX (2002 film)* top India's list). They need an anomaly filter.
- **Sources for humanities and place articles** are thin or noisy. OpenAlex and CrossRef are weak for Indian literature and villages. Google Books, Internet Archive or newspaper archives would cover these better.
- **Monolingual editors** still get no Discover suggestions; the reverse direction (articles important elsewhere but missing in English) isn't built.
- **Geo** is still the slowest call (p50 24 s), and WDQS calls can take up to 60 s (Commons & Wikidata max 61 s).
- **Local maintenance categories** that aren't hidden and have no Wikidata item (e.g. mlwiki "articles needing images") can still show up as an editor's "category".

### Not built yet
- Live alerts through EventStreams.
- OAuth login, for watchlist-based Revisit and logged-in Growth task lists.
- Toolforge deployment, and a persistent cache shared between workers.
- A feedback loop: did the editor act on a suggestion?
