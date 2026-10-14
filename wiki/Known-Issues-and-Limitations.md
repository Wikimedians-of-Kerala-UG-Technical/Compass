# Known Issues and Limitations

What's approximate or missing in Compass. Read this before trusting an output or planning work. The evaluation in `EVALUATION.md` and the playbook in `eval/README.md` measure most of these.

---

## Fixed in the October 2026 rewrite

| v1 problem | Now |
|---|---|
| Topics from a 12-keyword list (zoology → nothing; "india" a topic, Nigeria not) | Wikipedia's ML topic and country labels (`cirrusdoc`) |
| enwiki only | Home wiki detected per editor; `?wiki=` for any Wikipedia |
| Tasks were keyword searches (*Orlando: A Biography* for 9 of 15 editors) | `articletopic`/`articlecountry`/your categories/near you/similar to yours × tracking categories |
| `hastemplate:` matched nested templates | Tracking categories on enwiki; mapped local templates elsewhere |
| Pageviews looked up before the geo bonus, so 5–8 of every top 10 showed 0 | Looked up for the final top 30, then re-ranked |
| Geo focus ignored counts (Kentucky for Doc James) and used historical states | Count thresholds, ranks, P576 skipped, local place inside the region |
| `qualityTier` punished vandal fighters | Reverted by others, excluding self-reverts |
| Creations guessed from summaries (20 of 648) | `ucshow=new` |
| Revisit labelled "needs more references" as "Unreferenced"; no dates | Exact labels, tag dates, new-since-your-edit, revert-risk check |
| Discover alphabetical, wrong create link, empty for monolingual editors without saying why | CX recommender + sections, Content Translation links, explicit monolingual message |
| Guide's regex section splitter gave false alarms | Parsoid HTML: uncited paragraphs and dated inline tags |
| References suggested Wikipedia articles; Semantic Scholar always 429; PubMed by title words | Removed; key-gated; topic-routed PubMed reviews; Citoid templates; already-cited excluded |
| Trends global, two dead sources, DYK chrome | Country and home-wiki top articles that need work |
| Three HTTP clients, placeholder User-Agent, `debug=True`, hard-coded API base | One client, configurable UA, env config, `VITE_API_BASE` |
| Silent partial failures | `partial` + `failed` on responses, shown in the UI |

---

## Open issues

### Coverage
- **ML topic and country labels exist only on Wikipedias.** An editor who works almost only on Wikidata (e.g. Athulvis) still gets a profile from their small Wikipedia footprint. Their main value comes from Commons & Wikidata.
- **PageAssessments (quality class) exists on enwiki and a few others.** Elsewhere, feasibility relies on size alone. Lift Wing `articlequality` covers 11 wikis (not ml).
- **Tracking categories are sparse on some wikis** (mlwiki "All articles with unsourced statements": ~500 pages). Compass then uses the template, which can match nested templates.
- **Growth `hasrecommendation:` types vary by wiki.**
- **Edit-summary classification is English-only.** Tags cover the language-independent cases.

### Ranking
- The weights (0.30/0.20/0.15/0.15/0.10/0.10) are hand-set. A feedback loop (did the user edit the suggestion?) would let them be learned.
- "Biography" and "Media" are broad topics. For editors whose top topic is broad, the category and similar-article scopes matter most.

### Freshness and scale
- Caches (profile 6 h, signals 24 h, Wikidata places 7 days, trends 3 h) live in memory and in one SQLite file. That suits one machine; several machines would need a shared store such as Redis.
- A first visit is still slow for a very active editor: 2,000 contributions take four sequential API pages (~6 s), and a place hierarchy is walked one level at a time.
- WDQS queries can take 1–60 s and are rate-limited. Region gaps use direct P131 children only, because transitive queries over a whole state time out.
- Lift Wing and the CX recommendation API are used anonymously, which has rate limits. Register an API token for production volume.

### Not built yet
- Live alerts through EventStreams ("your article was just tagged").
- OAuth login for watchlist-based Revisit and logged-in Growth task lists.
- Toolforge deployment.
- A feedback loop and per-user history.
