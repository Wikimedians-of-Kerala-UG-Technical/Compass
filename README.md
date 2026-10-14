<h1 align="center">Compass</h1>

<p align="center">
  <strong>Your Wikipedia, Curated</strong><br>
  <sub>A personalized task recommender for Wikipedia editors.</sub>
</p>

---

## What is Compass?

Wikipedia has millions of articles that need work, but no good way to match editors with tasks suited to them. Existing tools hand everyone the same generic maintenance lists.

Compass does the opposite. You type in a Wikimedia username. It finds the Wikipedia that editor actually works on (Malayalam, Tamil, English…), studies their edits there, and returns work they'd recognise as theirs.

There are no accounts and nothing to sign up for. It reads public contributions only.

---

## What it does

1. **Profile.** Detects the editor's home wiki and languages, and reads Wikipedia's own ML topic and country labels for the articles they edit (e.g. *Films · India* on mlwiki, *Military and warfare · United States* on enwiki).
2. **Tasks.** Finds articles that need references, citations, links or images. It searches the editor's topics, the categories they edit in, places they write about, and articles similar to theirs. Results are ranked by topic match, place, impact, feasibility, tag age and the kind of edits they make, and each card says why it was picked.
3. **Revisit.** Their own articles that picked up tags (with dates, and "new since your last edit"), or whose latest edit by someone else looks like vandalism.
4. **Discover.** Articles and sections to translate into their languages, from Content Translation's recommender, plus articles about their district that are missing in their language.
5. **Commons & Wikidata.** Their photos that no article uses yet, with candidate articles, and Wikidata items near them missing a description in their language.
6. **Article Guide.** Points to the exact uncited paragraph, the dated `{{citation needed}}`, dead links, a Wikidata image to add, sections missing compared with English, and sources (PubMed reviews for medicine, OpenAlex, CrossRef) as ready-to-paste `{{cite journal}}`.
7. **Trends.** What readers in their country and on their wiki read yesterday that carries a maintenance tag.

---

## How it's built

```
frontend/   Vue 3 + Vite + Pinia + Wikimedia Codex
backend/    Flask API: one Wikimedia client (services/wiki.py), per-feature services, TTL caches (memory + SQLite)
eval/       Reproducible evaluation harness (see eval/README.md and EVALUATION.md)
legacy/     The original single-file prototype (inactive)
```

**Backend routes** (`backend/routes/`). Every per-user route accepts `?wiki=<dbname>`; the default is the editor's home wiki.

| Route | What it returns |
|---|---|
| `GET /api/profile/<username>` | Home wiki, languages, topics, countries, categories, creations, reverted-by-others |
| `GET /api/tasks/<username>` | Ranked tasks with reasons (`?lat&lon&place` adds "near you") |
| `GET /api/geo/<username>` | Places written about, and the focus region and district |
| `GET /api/revisit/<username>` | Own articles needing attention |
| `GET /api/discover/<username>` | Articles and sections to translate; local gaps |
| `GET /api/contribute/<username>` | Unused Commons photos; Wikidata gaps; campaigns |
| `GET /api/trends` | Most-read articles that need work (`?country&wiki&langs`) |
| `GET /api/article/<title>/guide` | Paragraph-level analysis |
| `GET /api/article/<title>/external-references` | Sources with citation templates |

Data sources: MediaWiki Action and REST APIs on any wiki, Wikidata and its Query Service, Commons, Pageviews, Lift Wing, Content Translation, Citoid, PubMed, OpenAlex and CrossRef. `WIKIMEDIA-RESEARCH.md` explains each one, and `python eval/probe_apis.py` checks that they all still answer.

---

## Running it locally

**Backend** (Flask, serves on `:5000`; see the wiki's Getting Started page for env vars):

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

---

## Documentation

Full developer documentation is available in our [GitHub Wiki](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki).

- [Home](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Home) — start here
- [Architecture](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Architecture) — how the pieces fit together
- [External APIs](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/External-APIs) — every API we call, and the exact parameters
- [API Reference](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/API-Reference) — request/response shapes for every endpoint
- [Known Issues and Limitations](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Known-Issues-and-Limitations) — what's approximate or fragile

Each feature has its own page: [Editor Profile](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Editor-Profile), [Task Recommendations](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Task-Recommendations), [Geographic Focus](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Geographic-Focus), [Revisit](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Revisit), [Discover](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Discover), [Commons & Wikidata](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Contribute), [Article Guide](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Article-Guide), [Trends](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Trends).

