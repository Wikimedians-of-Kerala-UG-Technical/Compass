# External APIs

Every piece of data comes from a public API. Nothing is stored, and nothing needs authentication. All calls go through `services/wiki.py`, which sets the User-Agent (override with `COMPASS_USER_AGENT`; [API etiquette](https://www.mediawiki.org/wiki/API:Etiquette) asks for contact details), retries on 429/5xx with backoff, and sends batches as POST.

`eval/probe_apis.py` re-checks every API below with live calls: `python eval/probe_apis.py`.

## Summary

| API | Endpoint | Used for |
|---|---|---|
| Action API, any Wikipedia | `https://{lang}.wikipedia.org/w/api.php` | Contributions, creations, Babel, categories, search, `cirrusdoc`, assessments, langlinks, revisions |
| Action API, Meta | `https://meta.wikimedia.org/w/api.php` | `globaluserinfo` (home wiki, per-wiki counts) |
| Action API, Commons | `https://commons.wikimedia.org/w/api.php` | `allimages`, `globalusage`, file coordinates |
| Action API, Wikidata | `https://www.wikidata.org/w/api.php` | `wbgetentities` (places, P18 image, dates, sitelinks) |
| REST API (Parsoid) | `https://{lang}.wikipedia.org/w/rest.php/v1/page/{title}/html` | Article Guide |
| CampaignEvents | `/w/rest.php/campaignevents/v0/event_discovery/discoverable_events?page=` | Campaigns that include your articles |
| Wikidata Query Service | `https://query.wikidata.org/sparql` | Region gaps; missing descriptions |
| Pageviews | `https://wikimedia.org/api/rest_v1/metrics/pageviews/…` | `per-article` (impact), `top` (per wiki), `top-per-country` |
| Lift Wing | `https://api.wikimedia.org/service/lw/inference/v1/models/revertrisk-language-agnostic:predict` | Suspicious latest edits on your articles |
| CX recommendations | `https://api.wikimedia.org/service/lw/recommendation/api/v1/translation[/sections]` | Discover |
| cxserver | `https://cxserver.wikimedia.org/v2/suggest/sections/{title}/{from}/{to}` | Guide: missing sections with translated headings |
| Citoid | `https://en.wikipedia.org/api/rest_v1/data/citation/mediawiki/{DOI|PMID}` | Ready-to-paste citations |
| PubMed E-utilities | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` | Medical sources (reviews) |
| OpenAlex | `https://api.openalex.org/works` | Scholarly sources |
| CrossRef | `https://api.crossref.org/works` | Scholarly sources (score ≥ 20) |
| Semantic Scholar | `https://api.semanticscholar.org/graph/v1/paper/search` | Only with `SEMANTIC_SCHOLAR_API_KEY` |

## Key Action API calls

| Call | Parameters | Notes |
|---|---|---|
| `meta=globaluserinfo` | `guiprop=merged|editcount` | Per-wiki edit counts; content Wikipedias identified by URL |
| `list=usercontribs` | `ucprop=title|timestamp|comment|sizediff|tags|size|ids|flags` | 4 × 500. Plus `ucshow=new&ucnamespace=0` for creations. |
| `meta=babel` | `babuser=` | Run on the home wiki. Babel is per wiki. |
| `prop=cirrusdoc|pageassessments|info` | `cdincludes=weighted_tags|popularity_score|incoming_links|text_bytes|coordinates|create_timestamp|timestamp|category|template`, `inprop=protection` | The main signal call, 50 titles per POST |
| `list=search` | `srsearch=<scope> <filter>` | Keywords: `articletopic:`, `articlecountry:` (ISO alpha-3), `incategory:"A|B"` (OR), `hastemplate:"A|B"`, `hasrecommendation:link|image`, `nearcoord:`, `morelikethis:` |
| `prop=langlinks` | `lllang=` | Maps English templates and categories to local names; seeds for CX |
| `prop=revisions` | `rvprop=user|timestamp|ids` | Latest revision of each article (Revisit) |
| `prop=categoryinfo` | | Skips huge categories; checks that tracking categories are populated |

## Gotchas

These are documented in full in `WIKIMEDIA-RESEARCH.md` §7:
- `hastemplate:` matches nested templates.
- `articlecountry:` takes alpha-3 codes, not names.
- Use POST for 50-title batches in non-Latin scripts.
- Babel is per wiki.
- `mw-reverted` includes self-reverts.
- WDQS transitive queries over a whole state time out.
- RESTBase (`/api/rest_v1/page/*`) is being retired; Compass uses `rest.php` for pages, and only Citoid still uses `/api/rest_v1`.
