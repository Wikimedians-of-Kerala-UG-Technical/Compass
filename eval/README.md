# Compass Evaluation Playbook

This folder holds a repeatable, hands-on evaluation of Compass. It is written so that **any AI agent (or person) can redo the test from scratch and produce a comparable evaluation report**. The first run (2026-10-13, v1 API) produced [`../EVALUATION.md`](../EVALUATION.md); its computed metrics are in [`baseline/2026-10-13-metrics.json`](baseline/2026-10-13-metrics.json). The re-run after the rewrite (v2 API) is in [`baseline/2026-10-13-v2-metrics.json`](baseline/2026-10-13-v2-metrics.json) and in §7 of `EVALUATION.md`.

The core question every run answers:

> **Does Compass give a real Wikimedia editor something they can act on, and is it *their* thing?**

Compass is meant for **any** Wikimedia editor, not only Kerala or India. The cohort and the rubric are built to catch tools that only work for one kind of editor.

---

## 0. Ground rules (read first)

1. **Read-only.** Never edit any wiki, post on talk pages, or contact the test users. Every script here only issues GET requests.
2. **Identify yourself.** Wikimedia APIs require a descriptive User-Agent. Set `COMPASS_EVAL_UA` if you want a contact address in it, e.g. `export COMPASS_EVAL_UA="CompassEval/1.0 (your-contact)"`. Never put someone else's email in it.
3. **Be gentle.** Run at most ~4 users concurrently. A full 15-user run makes several thousand API calls.
4. **Respect people.** Experienced editors in the cohort are public figures in the movement and are named. **Newcomers must be anonymised** ("Newcomer A/B") in every committed file and in the report.
5. **Verify, don't assume.** A claim Compass makes (a tag, a pageview count, a missing sitelink) is only "wrong" or "right" after you check it against live data with `verify.py`.
6. **Code first.** The harness mirrors the frontend's call sequence. If `frontend/src/stores/appStore.js` or `frontend/src/api.js` changed, update `harness.py` before running (see §2).

---

## 1. Files

| File | Purpose |
|---|---|
| `common.py` | Shared HTTP session, User-Agent, backend URL (`COMPASS_BACKEND`, default `http://127.0.0.1:5000`) |
| `harness.py` | Replays `appStore.start()` for each user and saves every endpoint's JSON and timing |
| `articles.py` | Exercises the Guide and External-references endpoints for chosen article titles (`--wiki` for other Wikipedias) |
| `ground_truth.py` | What each user *actually* does: per-wiki edits, enwiki share, Babel languages, real article creations |
| `verify.py` | Spot-checks: `pageviews`, `tags`, `shape`, `sitelinks`, `search`, `newcomers` |
| `digest.py` | Readable per-user dump you use when judging relevance |
| `metrics.py` | Automated cohort metrics, printed as tables and optionally saved as JSON |
| `probe_apis.py` | Re-verifies all 36 external APIs that [`../WIKIMEDIA-RESEARCH.md`](../WIKIMEDIA-RESEARCH.md) relies on (PASS/FAIL) |
| `cohort.md` | The standard test cohort and how to refresh it |
| `baseline/` | Committed metrics from past runs, for comparing runs over time |
| `runs/` | Raw outputs, **git-ignored** (≈9 MB per run) |

---

## 2. Procedure

Expect about 45–60 minutes wall-clock for 15 users, most of it waiting on the Geo and Discover endpoints.

### Step 1: Read the code (don't skip)
Read every file in `backend/routes/`, `backend/services/`, `frontend/src/stores/appStore.js` and `frontend/src/api.js`, plus `wiki/Known-Issues-and-Limitations.md`. You need this to (a) keep the harness faithful and (b) trace each bad output to a file and line in the report.

Check that `harness.py` still matches the frontend:
- the order of calls in `start()` and `fetchGeo()`'s `.finally`
- which parameters are sent: trends (`country` = `profile.countries[0].a2`, `wiki`, `langs`); tasks pass 2 (`geo.focus.local` coordinates); discover (`focus.region`/`focus.local` QIDs); contribute (`focus.local` or `focus.region`)
- any new endpoints or views. Add them to the harness, and add a row to the rubric table in §4.

### Step 2: Run the backend
```bash
python3 -m venv /tmp/compass-eval-venv
/tmp/compass-eval-venv/bin/pip install -r backend/requirements.txt
cd backend && /tmp/compass-eval-venv/bin/python -c "from app import create_app; create_app().run(port=5000, threaded=True)"
```
Run it in the background, without the debug reloader. Wait until `curl localhost:5000/api/trends` returns 200.

### Step 3: Pick the cohort
Use `cohort.md`. Keep the **core** users stable across runs so results are comparable. Refresh the **newcomers** every run:
```bash
python eval/verify.py newcomers     # pick 2 accounts with 40–400 edits, registered within ~2 months
```

### Step 4: Ground truth
```bash
RUN=eval/runs/$(date +%F)
python eval/ground_truth.py --out $RUN "Ranjithsiji" "Netha Hussain" ...   # all cohort users
```
This gives the cohort table for the report (§1 of the report): home wiki, enwiki share and declared languages.

### Step 5: Run the harness
Split the cohort into ~4 groups and run them in parallel:
```bash
python eval/harness.py --out $RUN --trends "Ranjithsiji" "Netha Hussain" "Athulvis" &
python eval/harness.py --out $RUN "Satdeep Gill" "Ravidreams" "Titodutta" &
...
wait
```
Each user produces `profile, trends, revisit, tasks1, geo, tasks2 (if a local focus resolved), discover, contribute` and `_timing.json`. A status of `-1` or non-200 is itself a finding; record it. `--trends` is only needed for the v1 API (global trends).

### Step 6: Article endpoints
Choose about 6 titles that cover these cases, and include a mix of articles from the users' own Revisit lists and their top tasks:
- a top task from the feed
- a Revisit item belonging to a test user
- a short article with a medical subject but **no medical word in its title**
- a large featured or good article (e.g. *Tuberculosis*)
- a village or place stub
- a biography
```bash
python eval/articles.py --out $RUN "Tuberculosis" "Koomapatti" "Lake Louise criteria" ...
```
Rerun any endpoint that fails once to tell transient failures from persistent ones.

### Step 7: Automated metrics
```bash
python eval/metrics.py $RUN --json eval/baseline/$(date +%F)-metrics.json
```
Rename newcomer folders in `$RUN` to `Newcomer A` and `Newcomer B` **before** writing the baseline JSON.

### Step 8: Judge relevance (the human-style part)
For each user run `python eval/digest.py $RUN "<user>"`. Using the ground truth (heavily-edited articles, top categories, home wiki), label each of the **top 10 tasks**:
- **R (relevant):** inside the user's demonstrated subject *or* place, *and* doable in one sitting.
- **P (plausible):** right broad country or topic but generic, or too big to finish in one sitting (e.g. "add citations to *Kerala*", 313 kB).
- **N (not relevant):** no connection to anything the user has done (e.g. *Orlando: A Biography* for a physician).

Record `R/P/N` counts per user in the report. Do the same, more lightly, for the first 5 items of Revisit and Discover.

### Step 9: Verify claims
For every feature, check at least 3 concrete claims against live data, and quote the results in the report:
```bash
python eval/verify.py pageviews "Kerala"                        # vs task 'pageviews'
python eval/verify.py tags "SARS-CoV-2" "Pekan, Pahang"         # vs Revisit labels
python eval/verify.py shape "Kerala Sahitya Akademi"            # is it really tractable?
python eval/verify.py sitelinks --wiki mlwiki "K. T. C. Abdullah"   # vs Discover 'missingIn'
```
Compare `createdDetected` (metrics) with `enwikiCreations` (ground truth) to check the profile's creation detection.

### Step 10: Test the alternatives you recommend
A recommendation is much stronger with proof. Before proposing a different search strategy, run it:
```bash
python eval/verify.py search 'hastemplate:"Citation needed" medicine' \
                             'hastemplate:"Citation needed" incategory:"20th-century Indian medical doctors"' \
                             'hastemplate:"More citations needed" nearcoord:40km,9.97,76.28'
python eval/verify.py search --wiki ml 'hastemplate:"Unreferenced" articletopic:films'
```

### Step 11: Score and write the report
Use the rubric in §4 and the report template in §6. Save it as `EVALUATION.md` (or `eval/reports/<date>.md` if you're keeping history) and link the baseline JSON.

---

## 3. Automated metrics: what they mean

Produced by `metrics.py`. Each comes with the 2026-10-13 baseline value.

| Metric | What it detects | Healthy | 2026-10-13 |
|---|---|---|---|
| `literalTop10` (per user) | Top-10 tasks whose title contains their own topic or place word, i.e. lexical matching | ≤ 2 | 10/10 for 9 of 15 users |
| `usersAllTop10Literal` | Users whose entire top 10 is lexical | 0 | 9 |
| `sharedTop10` | Top-10 titles that also appear in another user's top 10 | ≤ 1 unless users share a niche | 10/10 for all 3 Kerala users |
| `titlesIn3Plus` | Titles in ≥3 users' top 10 | none | *Orlando: A Biography* ×9, *Dictionary of National Biography* ×9 |
| `pv0Top10` | Top-10 tasks displaying 0 pageviews | 0 | 5–8 per user |
| `revisitWeakShare` | Revisit items tagged only stub or "could be expanded" | < 0.2 | 0.36 |
| `discoverEmpty` | Users given zero Discover suggestions | none | 4 (all monolingual) |
| `discoverLanguages` | Wikis treated as "your languages" | ≈ Babel / real languages | up to 77 |
| `createdDetected` vs ground truth | Creation detection accuracy | within 10% | 20 vs 648 (Netha Hussain), 20 vs 663 (Hog Farm) |
| `qualityTier` | Sanity check | prolific editors not "developing" | Doc James and Cwmhiraeth "developing" (v2 reports "reverted X%" here) |
| `personalTop10` (v2) | Top-10 tasks found via the user's own categories, articles or place | ≥ 3 | — |
| `hugeTop10` (v2) | Top-10 tasks on articles over 100 kB | ≤ 1 per user | — |
| `homeWikis` (v2) | Which wiki each profile was built on | matches ground truth | enwiki for everyone |
| `latency.*` median and max | Wait time | profile < 5 s; full dashboard < 20 s | profile 16 s (max 137); geo 76 s; discover 95 s |
| `nonOkStatuses` | Endpoint errors | none | none |

---

## 4. Rating rubric

Every feature is scored **0–10** as the sum of five dimensions, each scored **0, 0.5, 1, 1.5 or 2**. Write the breakdown down; it is what makes scores comparable between runs and agents.

| Dimension | 2 (good) | 1 (partial) | 0 (bad) |
|---|---|---|---|
| **Relevance / personalisation** | ≥ 70% of sampled items labelled R; clearly different per user | 30–70% R, or personal but noisy | < 30% R, or near-identical across users |
| **Actionability** | Editor knows exactly what to do, where, and can do it in one sitting; links go to the right place | Needs digging (which section? which tag?), or some links wrong | Nothing to act on, or actively misleading (e.g. Wikipedia articles offered as citations) |
| **Correctness** | Every spot-checked claim (≥ 3) verified true; labels accurate | Data true but mislabelled or partly wrong numbers | Claims false or fabricated (e.g. `pageviews: 0` for a 3,000/day article) |
| **Coverage** | Works for all cohort segments: non-English home wiki, monolingual, newcomer, prolific, every region | Fails one or two segments | Fails most segments or is enwiki-only for a cross-wiki need |
| **Performance & reliability** | p50 < 5 s, no silent failures, stable across reruns | p50 5–30 s, or some silent failures | p50 > 30 s, or a data source silently failing every time |

**Score bands**, as a sanity check on the sum:

| Band | Meaning |
|---|---|
| 9–10 | An editor would use this weekly without being told to |
| 7–8 | Useful now; defects are minor or cosmetic |
| 5–6 | Valuable core, but ranking, coverage or links make a big share unusable |
| 3–4 | Some signal, mostly generic or partly wrong |
| 1–2 | Mostly irrelevant or misleading; wastes the editor's time |
| 0 | Broken or erroring |

If the sum and the band disagree, re-examine your dimension scores rather than overriding the sum.

**Non-task features** (Profile, Geo data) feed other features rather than being acted on directly. For them, read *Relevance* as "does it describe the user accurately?" and *Actionability* as "is it usable as input for recommendations?"

**"Speed & reliability"** has its own scorecard row. Score it with the same 0–10 bands, using the latency table and the count of silently failing sources.

**Overall score** = the mean of all scorecard rows, rounded to the nearest 0.5.

### Calibration: the 2026-10-13 scores, broken down

Use this as the reference point. A future run should be able to say "Tasks moved from 0 → 1.5 on Relevance because…".

| Feature | Relevance | Actionability | Correctness | Coverage | Perf | **Total** | Decisive evidence |
|---|:-:|:-:|:-:|:-:|:-:|:-:|---|
| Revisit | 2 | 1.5 | 1.5 | 1 | 1 | **7** | All sampled tags real and the articles are the user's own; "needs more refs" shown as "Unreferenced"; 36% weak items; 0 items for newcomers; enwiki-only |
| Discover | 1.5 | 0.5 | 1.5 | 0.5 | 1 | **5** | Sitelinks verified missing; alphabetical not ranked; create-link opens a raw page instead of Content Translation; 4/15 users empty; 40–195 s |
| Geo (data) | 1 | 0.5 | 1.5 | 1.5 | 0.5 | **5** | Real P131 chains; chosen focus wrong for 5/15 (Kentucky, Hokkaido, Russian Empire ×2); 76 s median |
| Profile | 0.5 | 0.5 | 0.5 | 0.5 | 1 | **3** | Zoology editor profiled as biography; tier inverted; 20 of 648 creations detected; enwiki-only |
| Article Guide | 0.5 | 1 | 0.5 | 0.5 | 0.5 | **3** | Template advice; false "2 chars" on *Tuberculosis*; per-section ref counts useful; transient 5 s timeouts |
| External refs | 1 | 0.5 | 0.5 | 0.5 | 0.5 | **3** | Some right papers; Semantic Scholar 429 on 100% of calls; PubMed only on title keywords; nothing ready to cite |
| Tasks | 0 | 0.5 | 0.5 | 0 | 1 | **2** | 9/15 users all-lexical top 10; *Orlando* ×9; pv0 5–8/10; stable across reruns, 14 s |
| Trends | 0 | 0 | 0.5 | 0.5 | 1 | **2** | Not personalised; 2 of 5 sources empty; DYK admin junk; fast |
| Wikipedia "references" | 0 | 0 | 0 | 0.5 | 0.5 | **1** | Wikipedia articles offered as citations (WP:CIRCULAR) |
| Speed & reliability | — | — | — | — | — | **3** | Profile median 16 s (max 137 s); geo 76 s; discover 95 s; failures silent |
| **Overall** | | | | | | **3.5** | Mean 3.4, rounded to 3.5 |

The 2026-10-13 run assigned scores holistically and then decomposed them into this table. From the next run on, score the dimensions first and sum them. The v2 re-run did this; its breakdown, and the per-editor R/P/N labels, are in `EVALUATION.md` §7.

---

## 5. What to look for: known failure patterns

These were found in 2026-10-13. Check each one explicitly; it's a quick regression list.

- [ ] Same titles in many users' top 10 (`titlesIn3Plus`)
- [ ] Topic or place word in task titles (`literalTop10`)
- [ ] Tasks showing `pageviews: 0` for popular articles
- [ ] Geo focus chosen from a minor or historical place (dissolved states, ≤ 2 articles)
- [ ] `qualityTier` of "developing" for prolific patrollers
- [ ] Creation count far below `ucshow=new` ground truth
- [ ] Revisit labelling "needs additional references" as "Unreferenced"
- [ ] Discover empty for monolingual users; language list including `test*` or `abstractwiki`; alphabetical suggestions
- [ ] Discover create-link not using `Special:ContentTranslation`
- [ ] `/references` returning Wikipedia articles as citations
- [ ] Semantic Scholar returning 429 (check directly: `curl -s -o /dev/null -w "%{http_code}" "https://api.semanticscholar.org/graph/v1/paper/search?query=x&limit=1"`)
- [ ] Trends sources empty (`Category:Ongoing_events` missing) or the DYK parse returning admin chrome
- [ ] Profile reading enwiki only while the user's home wiki is elsewhere
- [ ] (v2) Tasks with `pageviews: null` in the top 10 (enrichment gap)
- [ ] (v2) Maintenance categories showing up in `topCategories` (e.g. tawiki "articles needing wikification")
- [ ] (v2) Discover pairs including languages the user doesn't declare in Babel
- [ ] (v2) `geo.focus.local` outside `geo.focus.region`
- [ ] (v2) `partial: true` on any response (which source failed?)

---

## 6. Report template

Write the report in this order. `../EVALUATION.md` is the worked example.

1. **Header:** the question, method summary (commit hash, date, cohort size, read-only), and a 3-sentence answer.
2. **Who I tested:** the ground-truth table (global edits, where they work, enwiki share, why included). Call out structural findings, e.g. how many users have a non-enwiki home wiki.
3. **Scorecard:** one row per feature: score, one-line verdict. Add the overall score. Put the dimension breakdown (§4 format) in an appendix or directly under it.
4. **Feature-by-feature:** for each feature:
   - how it works, with `file:line`
   - what came back, as a table of user → their niche → what Compass gave them
   - measured metrics
   - verified claims
   - what's good
   - root causes, with `file:line`
5. **What's genuinely good:** be specific; teams need to know what to keep.
6. **Recommendations:** P0 (days), P1 (structural), P2 (product). Back each with evidence, ideally an alternative query you actually ran (Step 10).
7. **Positioning:** compared with existing tools (Growth Suggested Edits, SuggestBot, Citation Hunt, Content Translation suggestions).
8. **Reproducing:** link this playbook, the baseline JSON, and the commit evaluated.
9. **Diff against the previous run:** score changes per dimension, and which §5 checks now pass.
