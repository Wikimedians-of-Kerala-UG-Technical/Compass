<p align="center">
  <img src="https://img.shields.io/badge/zero-dependencies-1d1b16?style=flat-square" alt="Zero dependencies">
  <img src="https://img.shields.io/badge/client--side-only-1d1b16?style=flat-square" alt="Client-side only">
  <img src="https://img.shields.io/badge/no-backend-1d1b16?style=flat-square" alt="No backend">
</p>

<h1 align="center">WikiTask Pro</h1>

<p align="center">
  <strong>Your Wikipedia, Curated</strong><br>
  <sub>A personalized task recommender for Wikipedia editors.<br>
  Enter your username. Get ranked, actionable tasks matched to your expertise.</sub>
</p>

<p align="center">
  <a href="https://nethahussain.github.io/wikitask-pro/"><strong>Open WikiTask Pro &rarr;</strong></a>
</p>

---

### The problem

Wikipedia has millions of articles that need work, but no good way to match editors with tasks suited to their skills. Existing tools show generic maintenance lists. WikiTask Pro is different -- it studies *you* first, then recommends accordingly.

---

### How it works

```
Username  -->  Edit history analysis  -->  Deep profile  -->  Ranked tasks
                     |                        |                    |
              500+ recent edits        Skill mapping         Scored by
              Category analysis        Topic focus           relevance,
              Edit type breakdown      Activity patterns     impact &
              Page info lookup         Quality tier          feasibility
```

WikiTask Pro runs entirely in your browser. No accounts, no backend, no data stored.

---

### Features

| | Feature | Description |
|---|---|---|
| &#x1F50D; | **Deep profiling** | Skill level, geographic focus, edit velocity, quality tier, active hours, article age preference |
| &#x26A1; | **20+ task types** | Orphans, dead-ends, bare URLs, disambig fixes, missing coords, uncategorized pages, BLP issues, wikification, short descriptions |
| &#x1F514; | **Watchlist alerts** | Articles you edited that have since degraded -- new issues flagged since your last contribution |
| &#x1F4CE; | **Reference discovery** | Section analysis, missing content detection, papers from Semantic Scholar, CrossRef & PubMed |
| &#x1F4F0; | **News & trends** | Trending topics and current events relevant to your editing areas |
| &#x1F3AF; | **Smart scoring** | Each task ranked by relevance, impact, feasibility, and urgency |
| &#x1F4F1; | **Mobile-ready** | Responsive design, works on any device |

---

### APIs

WikiTask Pro queries five public APIs -- all from the client, no keys required:

| Source | Data |
|:---|:---|
| MediaWiki Action API | Edit history, page metadata, categories, templates |
| Wikimedia Pageviews | Article traffic, trending pages |
| Semantic Scholar | Academic paper discovery |
| CrossRef | DOI and citation metadata |
| PubMed | Biomedical literature |

---

### Task scoring

Every task is scored across four dimensions:

```
Relevance   ████████░░  How well the task matches your topic expertise
Impact      ██████████  Article pageviews, importance, visibility
Feasibility ███████░░░  Estimated effort based on your skill profile
Urgency     █████░░░░░  Staleness, trending status, degradation signals
```

Tasks are ranked by a weighted composite. Filters let you narrow by topic, type, or difficulty.

---

### Quickstart

**Use it online** -- no install needed:

> **https://nethahussain.github.io/wikitask-pro/**

**Run locally:**

```bash
git clone https://github.com/nethahussain/wikitask-pro.git
cd wikitask-pro
open index.html
```

**Deploy your own:** Fork this repo, enable GitHub Pages on `main`, done.

---

### Stack

Vanilla HTML, CSS, and JavaScript. Single file. Zero dependencies.

Fonts: Newsreader (serif) / DM Sans (sans-serif) / JetBrains Mono (mono).

---

### License

Open source. Contributions welcome.
