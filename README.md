<h1 align="center">Compass</h1>

<p align="center">
  <strong>Your Wikipedia, Curated</strong><br>
  <sub>A personalized task recommender for Wikipedia editors.</sub>
</p>

---

## What is Compass?

Wikipedia has millions of articles that need work, but no good way to match editors with tasks suited to them. Existing tools hand everyone the same generic maintenance lists.

Compass does the opposite. You type in a Wikimedia username. It finds the Wikipedia that editor actually works on (Malayalam, Tamil, English…), studies their edits there, and returns work they'd recognise as theirs.

There are no accounts and nothing to sign up for. It reads public contributions only. Every screen has a shareable link, such as `/u/Ranjithsiji/tasks`.

---

## Behind Compass

Compass began as [WikiTask Pro](https://github.com/nethahussain/wikitask-pro), created by [Netha Hussain](https://github.com/nethahussain). The original prototype ran entirely in the browser, with no backend or dependencies (preserved in [`legacy/`](legacy/README.md)).


The technical team of the Wikimedians of Kerala User Group then built that idea into what Compass is now: a backend that works on any language Wikipedia and reads Wikipedia's own topic and country labels, tasks ranked by signals that each card explains, and the features listed below.

- [Netha Hussain](https://github.com/nethahussain)
- [Akash A](https://github.com/akashanil-dev)
- [Albin Jojo](https://github.com/albinjojo)
- [Edson Edwin Ninan](https://github.com/Edson-Edwin)
- [Mathews](https://github.com/MatthewsM2)

See the [GitHub contributors page](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/graphs/contributors) for contribution activity.

---

## What it does

1. **Profile.** Detects the editor's home wiki and languages, and reads Wikipedia's own ML topic and country labels for the articles they edit (e.g. *Films · India* on mlwiki, *Military and warfare · United States* on enwiki).
2. **Tasks.** Finds articles that need references, citations, links or images. It searches the editor's topics, the categories they edit in, places they write about, and articles similar to theirs. Results are ranked by topic match, place, impact, feasibility, tag age and the kind of edits they make, and each card says why it was picked.
3. **Revisit.** Their own articles that picked up tags (with dates, and "new since your last edit"), or whose latest edit by someone else looks like vandalism.
4. **Discover.** Articles and sections to translate into their languages, from Content Translation's recommender, plus articles about their district that are missing in their language.
5. **Commons & Wikidata.** Their photos that no article uses yet, with candidate articles, and Wikidata items near them missing a description in their language.
6. **Article Guide.** Points to the exact uncited paragraph, the dated `{{citation needed}}`, dead links, a Wikidata image to add, sections missing compared with English, and sources (PubMed reviews for medicine, OpenAlex, CrossRef) as ready-to-paste `{{cite journal}}`.
7. **Trends.** What readers in their country and on their wiki read yesterday that carries a maintenance tag, minus bot traffic.
8. **Your stats.** Edit streak, the last 30 days, and how many readers saw the articles they worked on.
9. **Feedback.** Vote on any task (good, done, not for me, hide). Votes shape their list and are stored with the ranking signals, so the weights can be fitted to real outcomes.
10. **Live alerts.** A notification when someone edits or tags one of their articles, straight from Wikimedia's EventStreams.
11. **Events.** Paste an edit-a-thon from Wikimedia's Event Registration and its worklist is ordered for you. Signup and progress stay on the official event page.

Newcomers (under 200 edits) get Wikipedia's guided link and image tasks. Monolingual editors get important articles missing in their language.

---

## How it's built

```
frontend/   Vue 3 + Vite + Pinia + vue-router + vue-i18n + Wikimedia Codex (light and dark)
backend/    Flask API: one Wikimedia client (services/wiki.py), per-feature services, TTL caches (memory + SQLite),
            a small SQLite store for task feedback; tests in backend/tests
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
| `GET /api/article/<title>/external-references` | Sources (journals, books, archives) with citation templates |
| `GET /api/stats/<username>` | Streak, last 30 days, readers reached |
| `POST /api/feedback`, `GET`/`DELETE /api/feedback/<username>` | Task votes (and undo), and which voted articles were then edited |
| `GET /api/alerts/<username>/stream` | Live alerts (server-sent events) |
| `/api/events…` | An Event Registration worklist, ranked for one editor |

Data sources: MediaWiki Action and REST APIs on any wiki, Wikidata and its Query Service, Commons, Pageviews, EventStreams, Lift Wing, Content Translation, Citoid, PubMed, OpenAlex, CrossRef, Open Library and the Internet Archive. `WIKIMEDIA-RESEARCH.md` explains each one, and `python eval/probe_apis.py` checks that they all still answer.

---

## Running it locally

**Backend** (Flask, serves on `:5000`; see [Getting Started](wiki/Getting-Started.md) for env vars):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cd backend && python app.py
```

**Frontend** (Vite dev server, expects the backend running on `:5000`):

```bash
cd frontend
npm install
npm run dev
```

**Tests and lint** (also run by CI on every pull request):

```bash
pytest && ruff check .
cd frontend && npm test
```

**Production:** `docker build -t compass . && docker run -p 8000:8000 -v compass-data:/data compass` serves the API and the app together. See [Getting Started](wiki/Getting-Started.md#production) for gunicorn and proxy settings.

---

## Documentation

Full developer documentation is available in our [GitHub Wiki](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki).

- [Home](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Home) — start here
- [Architecture](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Architecture) — how the pieces fit together
- [External APIs](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/External-APIs) — every API we call, and the exact parameters
- [API Reference](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/API-Reference) — request/response shapes for every endpoint
- [Known Issues and Limitations](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Known-Issues-and-Limitations) — what's approximate or fragile

Each feature has its own page: [Editor Profile](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Editor-Profile), [Task Recommendations](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Task-Recommendations), [Geographic Focus](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Geographic-Focus), [Revisit](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Revisit), [Discover](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Discover), [Commons & Wikidata](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Contribute), [Article Guide](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Article-Guide), [Trends](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Trends), [Stats & feedback](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Stats-and-Feedback), [Live alerts](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Live-Alerts), [Events](https://github.com/Wikimedians-of-Kerala-UG-Technical/Compass/wiki/Feature-Events).

---

## License

Compass is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License, version 3 or (at your option) any later version. See [LICENSE](LICENSE).

The original prototype was released into the public domain under CC0, which allows it to be included under this license.
