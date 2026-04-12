# WikiTask Pro

**Your Wikipedia, Curated** -- a personalized task recommender for Wikipedia editors.

Enter your Wikipedia username and WikiTask Pro analyzes your edit history, skill areas, and editing patterns to surface the most impactful tasks *for you*.

**Try it now:** [https://nethahussain.github.io/wikitask-pro/](https://nethahussain.github.io/wikitask-pro/)

---

## What it does

WikiTask Pro fetches your contribution history, builds a deep editor profile, and generates a ranked list of tasks tailored to your expertise and interests.

### Deep Personalization
Analyzes your skill level, geographic focus, edit velocity, quality tier, active hours, and article age preference to match you with relevant work.

### 20+ Quick-Win Task Types
Finds orphan articles, dead-end pages, bare URLs, disambiguation link fixes, missing coordinates, uncategorized pages, BLP issues, wikification needs, short description gaps, and more.

### Watchlist Alerts
Flags articles you previously edited that have since degraded -- new issues detected since your last contribution.

### Edit Guides & References
Provides section-level analysis, missing content detection, and discovers relevant academic papers from Semantic Scholar, CrossRef, and PubMed.

### Real-Time News & Trends
Surfaces trending topics and current events relevant to your editing areas so you can keep articles up to date.

---

## How it works

WikiTask Pro is a single-page client-side application (`index.html`) that runs entirely in the browser. No backend, no login, no data stored.

It queries the following APIs:

| API | Purpose |
|-----|---------|
| **MediaWiki Action API** | Edit history, page info, categories, templates |
| **Wikimedia Pageviews API** | Article traffic and trending pages |
| **Semantic Scholar API** | Academic paper discovery for references |
| **CrossRef API** | DOI and citation metadata |
| **PubMed API** | Biomedical literature references |

### Task scoring

Each task is scored and ranked using signals including:

- **Relevance** -- how well the task matches your topic expertise
- **Impact** -- article pageviews, importance, and visibility
- **Feasibility** -- estimated effort based on your skill profile
- **Urgency** -- staleness, trending status, degradation signals

---

## Setup

No build step required. Just open `index.html` in a browser, or deploy to any static hosting.

### Run locally

```bash
# Clone the repo
git clone https://github.com/nethahussain/wikitask-pro.git
cd wikitask-pro

# Open in browser
open index.html
```

### Deploy to GitHub Pages

Go to **Settings > Pages** in this repository, set the source to the `main` branch, and your site will be live at `https://nethahussain.github.io/wikitask-pro/`.

---

## Tech stack

- Vanilla HTML, CSS, and JavaScript -- zero dependencies
- Responsive design (mobile-friendly)
- Fonts: Newsreader (serif), DM Sans (sans-serif), JetBrains Mono (monospace)

---

## License

This project is open source. Contributions welcome.
