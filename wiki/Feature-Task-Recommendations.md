# Feature: Task Recommendations

**Endpoint:** `GET /api/tasks/<username>[?wiki=&lat=&lon=&place=]`
**Service:** `services/task_service.py` (with `signals.py` and `maintenance.py`)
**UI:** Tasks

Answers: *which articles that need work would this editor recognise as "theirs"?*

---

## 1. Candidates: scope × filter

Every candidate comes from a CirrusSearch query on the editor's home wiki that combines a **scope** taken from their footprint with a **filter** that selects articles needing work.

| Scope | Query fragment | Card reason |
|---|---|---|
| Topic + country (top 3 topics) | `articletopic:films articlecountry:ind` | "Films · India — a topic and country you edit a lot" |
| Topic only (top topic; or top 3 when no country) | `articletopic:biology` | "Biology — 24% of the articles you edit" |
| Your categories (top 3, preferring ones with ≥ 3 of your articles) | `incategory:"Kerala cuisine"` | "In “Kerala cuisine”, where you edited 23 articles" |
| Near your place | `nearcoord:25km,<lat>,<lon>` (from `geo.focus.local`) | "Within 25 km of Ernakulam district, where you edit" |
| Like your articles (top 2 most-edited) | `morelikethis:"<title>"` | "Similar to Battle of Goodrich's Landing, which you edited 77 times" |

| Filter | Query fragment |
|---|---|
| Maintenance (enwiki and wikis that use the tracking categories) | `incategory:"All articles lacking sources|All articles with unsourced statements|…"` (pipe = OR) |
| Maintenance (wikis that rely on templates) | `hastemplate:"<local names>"`, e.g. ml `തെളിവ്` |
| Growth suggestions (topic and near scopes only) | `hasrecommendation:link|image` |

**Why tracking categories, not `hastemplate:`.** On enwiki, `hastemplate:"Unreferenced"` also matches `{{Unreferenced section}}`, which uses `{{Unreferenced}}` internally. That made *Lok Sabha* show up as "unreferenced". The hidden category "All articles lacking sources" is exact.

**Other languages.** `maintenance.local_issues(dbname)` maps each English template and category to its local name through interlanguage links (cached for 7 days). The category is used when the wiki actually populates it (≥ 1,000 pages, or always on enwiki); otherwise the template is used.

## 2. Signals

All candidates (typically 300–500) are read through `prop=cirrusdoc|pageassessments|info`, 50 per call and 4 calls in parallel. The editor's own articles are excluded (Revisit covers those), and so are protected pages. Each article's issues come from its categories or templates; the primary issue is the most urgent one.

## 3. Ranking

```
score = 0.30·topic        cosine(editor topic vector, article topic weights)
      + 0.20·place        article country is the editor's #1/#2/#3 country (1/.7/.5), or ≤ 50 km from their place
      + 0.15·impact       popularity_score (the article's share of its wiki's views, from cirrusdoc) + Top/High importance
      + 0.15·feasibility  < 15 kB = 1 … > 100 kB = 0.1; Stub/Start/C +; GA/FA halved; quick issue types +
      + 0.10·freshness    tag age from the dated tracking category (≤ 1 yr = 1 … > 8 yrs = 0.2)
      + 0.10·affinity     how often the editor does this kind of edit (references, linking, media…)
      + 0.05·urgency      per issue type
      + 0.05              if found through the editor's own categories, articles or place
      − 0.05              Growth quick tasks for experienced editors (≥ 500 home-wiki edits)
```

Impact uses `popularity_score` because it comes in the same batch call for every candidate, and it's relative to the article's own wiki, which suits small wikis. Real 30-day pageviews (`metrics/pageviews/per-article/<lang>.wikipedia/all-access/user/…`) are fetched only to *display* on the top 30 cards. If that API rate-limits, the number is left off and the response is marked `partial`; the ranking doesn't change. v1 used pageviews for ranking but fetched them before the geo bonus, so 5–8 of every top 10 showed 0.

**Diversity.** No scope supplies more than 5 of the leading tasks, and no task type more than 15. The rest still follow, in score order. The response keeps the top 60.

## 4. What a card shows

The title, the action ("Add references · ~20 min"), every issue with its tag date, the reason, and details ("Start-class · 6 kB · tagged since 2026-02 · 53 views/day"). Buttons go to the edit page and to the Guide, which shows exactly where in the article the problem is. Four small buttons record feedback (good suggestion, I did this, not for me, hide); see [[Feature-Stats-and-Feedback]]. Cards voted down, done or hidden don't come back for that editor.

## Newcomer mode

Editors with **fewer than 200** edits on the home wiki are in **guided mode** (`mode: "guided"`): only Growth's `hasrecommendation:link|image` tasks, searched in every one of their scopes plus the whole wiki (so an editor with no clear topic still gets tasks). These come with step-by-step help in the editor, and a handful of edits says too little about someone to pick real gaps. When the newcomer is logged in, Tasks also lists Growth's own suggestions for the topics they chose on Special:Homepage (`/api/me/newcomer-tasks`).

Editors with < 500 edits on the home wiki get full affinity for Growth "add a link / add an image" tasks, and never get articles over 60 kB or GA/FA-class articles. Those are machine-prepared, take about 5 minutes, and Growth's own tools on the wiki guide the edit.
