# Feature: Discover

**Endpoint:** `GET /api/discover/<username>[?wiki=&region=&local=&regionName=]`
**Service:** `services/discover_service.py`
**UI:** Discover

Answers: *what could this editor translate into their language that fits what they already write?*

---

## Language pairs

- Source is English if the editor knows it (Babel or ≥ 100 edits), else their home language.
- Targets are every other language they know, up to 3.

Example: Ranjithsiji → `en → ml`. An editor with no second language gets `monolingual: true`, and the UI explains how a Babel box would enable suggestions.

## Articles to translate

The Content Translation recommendation API (`api.wikimedia.org/service/lw/recommendation/api/v1/translation`), the same engine behind CX's own suggestions:
- **Seeded** with the editor's 5 most-edited articles, mapped to the source language through langlinks: "Related to Nedumudi Venu, Koomapatti".
- **By topic**, with the editor's top 2 topics and their country: `topic=films&country=ind`.

Within each group, results are ranked by how many languages already have the article. The groups are interleaved. Each item links to `Special:ContentTranslation?page=…&from=en&to=ml`.

v1 sampled category members alphabetically, so lists started at "Aaryan…". It linked to `ml.wikipedia.org/wiki/<English title>`, which would create a Malayalam page under an English title. It also returned nothing for monolingual editors without saying why.

## Missing sections

`translation/sections`, seeded with the same articles, finds articles that exist in both languages where the target lacks sections. The headings come already translated: Plot → കഥാസാരം. Each section links to Content Translation with `sourcesection=` set. Reference-type sections are dropped.

## Missing near you

A Wikidata Query Service query for items located **directly** (P131) in the editor's focus district or region that have an English article but none in the target language, ordered by sitelink count. Transitive `P131+` over a whole state times out on WDQS, which is why it uses direct children only. Results are cached 24 h.

The whole response is cached 6 h.
