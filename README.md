<h1 align="center">Compass</h1>

<p align="center">
  <strong>Your Wikipedia, Curated</strong><br>
  <sub>A personalized task recommender for Wikipedia editors.</sub>
</p>

---

## What is Compass?

Wikipedia has millions of articles that need work, but no good way to match editors with tasks suited to their skills. Existing tools just dump generic maintenance lists on everyone.

Compass does the opposite: type in a Wikipedia username, and it studies that editor's own history first — what topics they write about, how they edit, what quality bar they hold themselves to — and only then hands back a ranked list of articles worth their time.

There are no accounts and nothing to sign up for. You give it a public Wikipedia username, it reads that user's public contributions, and it returns recommendations.

---

## What it does

1. **Builds a profile from edit history** — pulls an editor's recent contributions and figures out their topic focus, edit types, activity patterns, and skill/quality tier.
2. **Finds candidate tasks** — searches Wikipedia for articles matching the editor's topics that need references, are orphaned, or are tagged "citation needed."
3. **Watches articles the editor already touched** — flags pages they previously edited or created that have since picked up new issues, so there's a natural follow-up trail.
4. **Scores and ranks everything** — each task is weighted by relevance to the editor's interests, the article's impact (pageviews/importance), how feasible it is given their skill level, and urgency (staleness, trending status).
5. **Surfaces context to help them act** — trending topics, relevant news, and per-article guides with suggested references pulled from Semantic Scholar, CrossRef, and PubMed.

---

## How it's built

The project is split into a frontend and a backend that talks to Wikipedia and a few academic APIs on the frontend's behalf.

```
frontend/   Vue 3 + Vite single-page app — onboarding, dashboard, task list, article guide
backend/    Flask API — builds profiles, discovers tasks, scores/ranks them
legacy/     The original single-file vanilla JS prototype (kept for history, no longer active)
```

**Backend routes** (`backend/routes/`):
- `GET /api/profile/<username>` — builds an editor profile from their contribution history
- `GET /api/tasks` — finds and ranks candidate tasks for the current profile
- `GET /api/trends` — current trending Wikipedia topics and news
- `GET /api/article/<title>/guide` — structural analysis and editing suggestions for one article
- `GET /api/article/<title>/references` and `/external-references` — suggested citations

**Frontend flow** (`frontend/src/App.vue`): user enters a username → app calls the profile, trends, and tasks endpoints in parallel → renders a dashboard with the profile summary, trending/news sidebars, the ranked task list, and an article guide panel for digging into a specific task.

Data sources: the MediaWiki Action API and Wikimedia Pageviews for everything Wikipedia-side, plus Semantic Scholar, CrossRef, and PubMed for reference discovery.

---

## Running it locally

**Backend** (Flask, serves on `:5000`):

```bash
cd backend
pip install -r requirements.txt
python app.py
```

**Frontend** (Vite dev server, expects the backend running on `:5000`):

```bash
cd frontend
npm install
npm run dev
```
