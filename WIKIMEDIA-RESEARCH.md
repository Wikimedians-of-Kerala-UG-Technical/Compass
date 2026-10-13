# Wikimedia Platform Research: What Compass Can Build On

> **Purpose.** This is a working expert's guide to how Wikipedia, Wikidata and Commons are structured, which signals and APIs they expose, and how each one maps to a concrete improvement in Compass.
>
> **How it was verified.** Every API, search keyword and data source marked ✅ was **called live on 2026-10-13** with real articles and users, and the result is quoted. ⚠️ means it works with a caveat. ❓ means it's documented but couldn't be verified without logging in. You can re-run the checks with `python eval/probe_apis.py`.
>
> **Companion documents:** [`EVALUATION.md`](EVALUATION.md) (what's wrong today) and [`eval/README.md`](eval/README.md) (how to re-test).

---

## Contents
1. [How the Wikimedia ecosystem fits together](#1-how-the-wikimedia-ecosystem-fits-together)
2. [Anatomy of a Wikipedia article](#2-anatomy-of-a-wikipedia-article)
3. [The maintenance system: how Wikipedia marks "work needed"](#3-the-maintenance-system)
4. [Wikidata and Commons for Compass](#4-wikidata-and-commons)
5. [API catalogue (verified)](#5-api-catalogue-verified)
6. [Signals catalogue: every factor Compass can rank on](#6-signals-catalogue)
7. [Gotchas we hit](#7-gotchas-we-hit)
8. [Applying this to Compass: feature-by-feature redesign](#8-applying-this-to-compass)
9. [Proof of concept: ML-tag profiles](#9-proof-of-concept-ml-tag-profiles)
10. [Roadmap](#10-roadmap)
11. [Sources](#11-sources)

---

## 1. How the Wikimedia ecosystem fits together

```
                       ┌──────────────── Wikidata (www.wikidata.org) ────────────────┐
                       │ one item per concept: Q1186 = Kerala                         │
                       │ labels/descriptions in 300+ languages · statements (P131,    │
                       │ P625, P18 …) · SITELINKS → which wikis have an article       │
                       └───────▲──────────────────▲─────────────────────▲─────────────┘
                               │ sitelinks        │ sitelinks           │ P18 image / P373 category
  en.wikipedia ◄───────────────┤                  │                     │
  ml.wikipedia (Malayalam) ◄───┤   ~340 Wikipedias, each an independent wiki with its own
  ta / pa / sw / yo …     ◄────┘   community, templates, policies and maintenance categories
                                                                         │
                       ┌───────────────── Commons (commons.wikimedia.org) ┴────────────┐
                       │ shared media repository · categories · Structured Data (P180)  │
                       └───────────────────────────────────────────────────────────────┘
   Global account (SUL): one username across every wiki. Edits, rights and Babel are per wiki.
```

Key facts for Compass:

| Concept | What it means | Why Compass cares |
|---|---|---|
| **Wiki / dbname** | Each project is a separate MediaWiki install: `enwiki`, `mlwiki`, `wikidatawiki`, `commonswiki` | Compass talks only to `en.wikipedia.org`. Everything below works on *any* Wikipedia by changing the host. |
| **SUL global account** | One username everywhere. `meta=globaluserinfo` lists every wiki and its edit count. | Find each user's **home wiki**. Ranjithsiji: Wikidata 295k, Commons 98k, mlwiki 26k, enwiki 3.2k. |
| **Namespaces** | 0 = articles, 1 = talk, 2 = user, 4 = project, 6 = file, 10 = template, 14 = category, 118 = draft | Filter contributions; templates and categories carry the maintenance signals. |
| **Independent communities** | Template names, categories and policies differ per language | Map templates through their **Wikidata item** (see §3.4), never hard-coded English names. |
| **Wikidata as the hub** | Every article links to one item; the item knows every language version | Cross-language gaps, coordinates, images, places and occupations without parsing text. |
| **WikiProjects** | Volunteer groups per topic (Medicine, India, Women in Red…) that assess articles | Quality class and importance per article (§2.3). |
| **Growth features** | Newcomer homepage plus ML "structured tasks" (add a link, add an image) | Already-computed task pools Compass can search (§5.2). |
| **Toolforge / Cloud VPS** | Free community hosting (XTools, PetScan, Citation Hunt…) | Compass could be hosted there, and can use these tools' APIs. |

---

## 2. Anatomy of a Wikipedia article

### 2.1 The parts, and where each lives in the data

Parsed live from Parsoid HTML of *Nedumudi Venu*, *Koomapatti*, *Kerala Sahitya Akademi* and *Erachichor* (`GET /w/rest.php/v1/page/{title}/html`).

| Part | How to detect it | Live example | Compass use |
|---|---|---|---|
| **Short description** | `{{Short description}}`, or `prop=description` / `pageprops.wikibase-shortdesc` | "Indian actor and screenwriter (1944–2021)" | Card subtitle; a missing one is a 1-minute task |
| **Hatnotes** | `{{About}}`, `{{For}}`, `{{Distinguish}}` | — | Ignore when counting prose |
| **Maintenance banners** | Transclusions with a `date` parameter at the top; class `ambox` | `More citations needed`, date **April 2022** | Task type and tag **age** |
| **Infobox** | `{{Infobox …}}` (`data-mw`) | `infobox person`, `infobox settlement` | Missing infobox; infobox fields vs Wikidata |
| **Lead section** | `<section data-mw-section-id="0">` | 1,517 chars (Nedumudi Venu) | "Lead too short" checks; summary on cards |
| **Sections** | `<section data-mw-section-id=N>` with `h2`/`h3` | Early life, Death, Filmography, Awards… | Section-level tasks (§8.5) |
| **Inline citations** | `typeof="mw:Extension/ref"` → `<sup class="mw-ref">` | 30 refs | Citation density per section and paragraph |
| **Citation templates** | `cite web`, `cite news`, `cite book`, `cite journal` | 15 news, 11 web, 2 book | Source mix; bare URLs |
| **Inline maintenance tags** | `{{cn}}`, `{{dead link}}`, `{{failed verification}}`, `{{clarify}}`, `{{who}}`, each with a date | `cn`, July 2026 (Koomapatti) | **The** most precise tasks: one sentence, one fix |
| **Uncited paragraphs** | `<p>` with > 80 chars and no ref inside | *Early life*: "Venu was born as K. Venugopal at Nedumudi…" | Paragraph-level "needs a source" without any tag |
| **Images** | `typeof="mw:File…"` figures | 5–13 per article | "Add an image" when 0 and Wikidata has P18 |
| **Coordinates** | `{{Coord}}`; `cirrusdoc.coordinates` | Kerala: 8.5, 77, region KL | `nearcoord:` search; local tasks |
| **See also / External links** | Standard section names | — | Excluded from prose metrics |
| **References list** | `{{Reflist}}` / `<references/>` | — | Missing reflist means broken refs |
| **Navboxes, authority control** | `{{Navbox}}`, `{{Authority control}}` | `authority control` | Low priority |
| **Stub template** | `{{…-stub}}` → `Category:… stubs` | `tamilnadu-geo-stub` | Stub expansion tasks by topic |
| **Categories** | Visible and hidden (`clshow=hidden`) | `Articles lacking reliable references from June 2021` | Topic scoping; dated maintenance |
| **Language links** | `rest.php/v1/page/{t}/links/language` or Wikidata sitelinks | Koomapatti → ta, ur | Translation gaps |

### 2.2 The talk page
`Talk:<title>` carries `{{WikiProject banner shell}}` with one `{{WikiProject X|class=…|importance=…}}` per project, plus `{{Article history}}`, `{{DYK talk}}` and `{{Old XfD multi}}`. Example: *Talk:Nedumudi Venu* has `WikiProject banner shell` and `WikiProject India`. **Don't parse talk pages yourself. PageAssessments (§2.3) exposes the same data.**

### 2.3 Quality and importance (PageAssessments) ✅
`prop=pageassessments` returns the class and importance assigned by each WikiProject:

```
Tuberculosis           Medicine: GA/Top · Microbiology: GA/Top
Kerala Sahitya Akademi India: Stub/Low
Koomapatti             India: Stub/Low (WikiProject Tamil Nadu)
```
- **Quality scale (enwiki):** Stub → Start → C → B → GA → A → FA. Featured lists use FL. Other wikis vary or don't assess at all (mlwiki uses the template badges in §6).
- **Importance:** Top / High / Mid / Low / NA.
- **`list=projectpages&wppprojects=Medicine&wppassessments=1`** ✅ lists *every* article in a WikiProject with its assessment. That's a ready-made, community-curated topic pool.
- ML alternatives: the Lift Wing `articlequality` model (§5.6) predicts the class for any revision on 11 wikis, and `cirrusdoc` includes the assessment projects too.

### 2.4 Reading article content: the right way
| Method | Use for | Status |
|---|---|---|
| **Parsoid HTML** `GET /w/rest.php/v1/page/{title}/html` | Structure: sections, refs, every template with **its parameters** in `data-mw` (e.g. `{"template":{"target":{"wt":"refimprove"},"params":{"date":{"wt":"July 2025"}}}}`) | ✅ Recommended |
| `action=parse&prop=wikitext` | Raw source; `insource:` checks | ✅ Regex parsing is fragile (Compass's "Expand Causes (2 chars)" bug comes from this) |
| `prop=extracts` (TextExtracts) | Plain-text lead for cards | ✅ |
| `/api/rest_v1/page/summary` | Card data: description, thumbnail, coordinates | ⚠️ RESTBase is being retired; prefer `rest.php` and Action API equivalents |
| XTools `page/prose` | Words, refs, sections counted | ✅ e.g. Koomapatti: 76 words, 6 refs |

---

## 3. The maintenance system

This is how Wikipedia marks "work needed", and it's the backbone of any task recommender.

### 3.1 Two kinds of tags
- **Banner (article-level):** `{{More citations needed|date=April 2022}}`, `{{Unreferenced}}`, `{{Orphan}}`, `{{Underlinked}}`, `{{Dead end}}`, `{{Copy edit}}`, `{{Update}}`, `{{Expand section}}`, `{{Lead too short}}`, `{{One source}}`, `{{Primary sources}}`, `{{Notability}}`, `{{Tone}}`, `{{Advert}}`, and `{{Multiple issues}}` as a wrapper.
- **Inline (sentence-level):** `{{Citation needed}}`/`{{cn}}`, `{{Dead link}}`, `{{Failed verification}}`, `{{Better source needed}}`, `{{Clarify}}`, `{{Who?}}`, `{{When?}}`, `{{Page needed}}`, `{{Update inline}}`. These are the most actionable because the fix is local.

### 3.2 Tracking categories: the precise index ✅
Every dated tag puts the article into **hidden** categories:
- `Category:All articles with unsourced statements` (always)
- `Category:Articles with unsourced statements from October 2026` (dated)

Live counts on enwiki:

| Tracking category | Articles |
|---|---:|
| All articles with unsourced statements | 585,985 |
| All articles needing additional references | 542,252 |
| All articles with dead external links | 359,362 |
| All articles lacking in-text citations | 109,645 |
| All articles with topics of unclear notability | 55,875 |
| All orphaned articles | 53,102 |
| All articles to be expanded | 52,485 |
| All articles lacking sources (fully unreferenced) | 32,240 |
| All articles with failed verification | 17,524 |
| Articles with unsourced statements from October 2026 | 15,791 |
| All stub articles | 2,315,564 |

**Use `incategory:"All articles lacking sources"` rather than `hastemplate:"Unreferenced"`.** `hastemplate` also matches templates nested inside other templates. *Lok Sabha* and *French language* both match `hastemplate:"Unreferenced"`, because `{{Unreferenced section}}` uses `{{Unreferenced}}` internally. Compass's task search has this bug today. ✅ verified: `incategory:"All articles lacking sources" articlecountry:ind` returns 912 genuinely unsourced Indian articles (*Aralikatti*, *Nesargi*, *Chorla*…).

### 3.3 Tag age is a signal
The dated subcategory, or the `date=` parameter in `data-mw`, says *how long* the problem has existed. Use it to:
- surface **new** problems on a user's own articles (Revisit: "tagged after your last edit");
- prefer fresh `{{cn}}` tags (likely about recent claims, so sources are easier to find), or offer "oldest unresolved" lists to experienced editors.

### 3.4 Other languages: map templates through Wikidata ✅
Templates link across languages through their Wikidata items, the same way articles do:

| enwiki template | Wikidata | mlwiki equivalent |
|---|---|---|
| Unreferenced | Q5962027 | ഫലകം:Unreferenced |
| More citations needed | Q5619503 | ഫലകം:More citations needed |
| Citation needed | Q5312535 | **ഫലകം:തെളിവ്** |
| Orphan | Q5754827 | ഫലകം:Orphan |
| Expand section | Q5623589 | **ഫലകം:അപൂർണ്ണവിഭാഗം** |
| Copy edit | Q6292692 | ഫലകം:Copy edit |

`prop=langlinks&lllang=ml` on the English template gives the local name; then search `hastemplate:` or find its tracking category on that wiki. Never hard-code English names.

### 3.5 Special-page maintenance reports ✅
`list=querypage` returns the wiki's cached maintenance reports. Verified on mlwiki (refreshed 2026-10-13):

| `qppage` | What it lists |
|---|---|
| `Lonelypages` | Orphans: no incoming links |
| `Deadendpages` | No outgoing links |
| `Wantedpages` | Most-linked **red links**, i.e. missing articles readers are already pointed to |
| `Withoutinterwiki` | Not linked to any other language |
| `Uncategorizedpages` | No categories |
| `Ancientpages` | Least recently edited |
| `Shortpages` | Shortest articles |
| `Unusedimages` | Local files used nowhere |

These work on small wikis that lack an enwiki-style tagging culture.

---

## 4. Wikidata and Commons

### 4.1 Wikidata properties Compass should know
| Property | Meaning | Use |
|---|---|---|
| P31 / P279 | instance of / subclass of | Article type (human Q5, village, film…) |
| P131 | located in administrative territory | Place hierarchy (Compass's `geo_service` walks this) |
| P17 | country | Country rollup |
| P625 | coordinates | `nearcoord:` searches |
| P18 | image | "Add an image": the item has a photo, the article doesn't |
| P373 | Commons category | Find photos for an article |
| P19 / P27 | place of birth / citizenship | Geo for biographies (**use preferred rank**, not `claims[0]`) |
| P106 / P21 | occupation / sex or gender | Women in Red-style gap lists |
| P576 | dissolved / abolished | Drop historical states from geo focus (Russian Empire, Kingdom of Great Britain) |
| P248 / P854 | stated in / reference URL | Wikidata references reusable as article citations |
| sitelinks | Articles in each wiki | Translation gaps; sitelink count as an importance proxy |

### 4.2 Wikidata Query Service (SPARQL) ✅ ⚠️
`https://query.wikidata.org/sparql` answers gap questions no other API can. Live results:

| Query | Top results | Time |
|---|---|---:|
| Places in Kerala with an enwiki article but **no mlwiki** article, by sitelink count | Puthunagaram, Mulavukad, Nenmanikkara, Chengamanad (plus wrongly-located *Kali River*) | 23.5 s |
| Indian women physicians (P106 = Q39631) missing on mlwiki | Swati Piramal, Uma Saren, Soniya Nityanand, Killi Krupa Rani | 54.6 s |
| Ernakulam-district items **on mlwiki with no Malayalam description** | Kundannoor flyover, Karingachira Church, Kerala High Court | 0.7 s |
| Ernakulam items with a P18 image | Bolgatty marina, JLN Stadium Kochi, Santa Cruz Basilica | 3.9 s |

Caveats:
- Queries can take 1–60 s, so precompute and cache them; never run them per page load.
- Data has errors (*Kali River* is placed in Kerala).
- **Graph split (May 2025):** scholarly articles were moved to a separate endpoint. Citation-metadata queries need the scholarly graph or federation.

**Wikibase REST API** ✅ `GET https://www.wikidata.org/w/rest.php/wikibase/v1/entities/items/Q1186/labels` returns `{en: Kerala, ml: കേരളം, ta: கேரளம், hi: केरल}`.

### 4.3 Commons for photographers ✅
- **Uploads:** `list=allimages&aiuser=<user>&aisort=timestamp`
- **Usage:** `prop=globalusage` shows which articles, on which wikis, use each file. **14 of Ranjithsiji's last 20 uploads are used in no article** (Fort Kochi beach series, *Myristica fragrans*, Changampuzha Park station…). That's a perfect "place your photos" task.
- **Structured Data on Commons:** `wbgetentities&ids=M<pageid>` returns `P180` (depicts). His latest file has **no depicts statement**, which is a quick Commons task. Search with `haswbstatement:P180=Q1800` (139 files depict Ernakulam).

---

## 5. API catalogue (verified)

Use **one** HTTP client with a descriptive User-Agent, `maxlag=5`, 429/`Retry-After` handling, **POST** for batched title lists (50 titles in Tamil script overflowed a GET URL in testing), and `formatversion=2`.

### 5.1 MediaWiki Action API (`https://{wiki}/w/api.php`)
| Module | Gives | Status | Compass use |
|---|---|---|---|
| `meta=globaluserinfo&guiprop=merged` | Per-wiki edit counts | ✅ | Home wiki |
| `meta=babel&babuser=` | Declared languages, **per wiki** | ✅ ⚠️ Netha Hussain's Babel is only on Wikidata (`ml-N, en-5, sv-4, kn-4, hi-3`). Query her top wikis. | Real languages for Discover |
| `list=usercontribs` with `ucprop=tags\|sizediff`, `ucshow=new` | Edits; creations; **edit tags** | ✅ | Profile |
| — tag `mw-reverted` | Edit later reverted | ✅ ⚠️ includes self-reverts | Replace `qualityTier` |
| — tags `visualeditor`, `contenttranslation`, `shortdesc helper`, `editsuggestion-seen`, `newcomer task`, `discussiontools` | Which tool made the edit | ✅ | Edit-type affinity without parsing summaries |
| `prop=pageassessments` / `list=projectpages` | WikiProject class and importance | ✅ | Ranking; topic pools |
| `prop=info&inprop=watchers\|protection` | Watchers (≥ 30 shown), protection | ✅ Kerala: 1,135 watchers, extended-confirmed protected | Skip protected pages for newcomers |
| `prop=pageprops\|description\|pageimages\|extracts` | QID, short description, lead image, lead text | ✅ | Cards |
| **`prop=cirrusdoc`** | The search index's document: **ML topic and country scores, Growth recommendation flags, assessment projects**, popularity, incoming links, coordinates, templates, headings, categories, `text_bytes` | ✅ | **One call per 50 pages gives everything for profiling and ranking** (§9) |
| `prop=categories&clshow=hidden` | Tracking categories with dates | ✅ | Revisit tags and age |
| `prop=templates&tltemplates=` | Is template X present (incl. nested) | ✅ | Confirm a tag |
| `prop=revisions&rvuser=` | User's last edit on a page | ✅ | "Tagged after your last edit" |
| `prop=langlinks` | Language versions | ✅ | Template and article mapping |
| `prop=globalusage` (Commons) | Where a file is used | ✅ | Photographer tasks |
| `list=querypage` | Orphans, dead ends, wanted pages… | ✅ | Small-wiki tasks |
| `list=linterrors` | Markup errors by category | ✅ | Gnome tasks |
| `list=growthtasks` | Growth's task pool | ❓ requires login (internal module) | Use `hasrecommendation:` search instead |
| `list=watchlistraw` | User's watchlist | ❓ needs OAuth | Optional "your watchlist" mode |

### 5.2 Search (CirrusSearch): `list=search&srsearch=…`
| Keyword | Example (live hits) | Notes |
|---|---|---|
| `incategory:` | `incategory:"All articles lacking sources"` | Exact category, no subcategories |
| `deepcat:` | `deepcat:"Radiologic signs"` | Subcategories up to depth 5 / 256 categories |
| `articletopic:` | `articletopic:medicine-and-health` (15,835 with cn) | ML topics; Wikipedias only; `\|` = OR, space = AND |
| **`articlecountry:`** | `articlecountry:ind` (**ISO alpha-3**; `India` returns 0) | ML country model. `nga`+women+refs: 21; `zaf`+orphan: 391 |
| **`hasrecommendation:`** | `link` (en 584k / ml 17k), `image` (54k / 7.7k), `image_section` (40k / 1.4k), `tone>0.8` (9.6k) | Growth's precomputed structured tasks; varies by wiki |
| `morelikethis:` | `morelikethis:"Lake Louise criteria" hastemplate:"More citations needed"` → cardiology (188) | `morelike:` can't be combined with filters; `morelikethis:` can |
| `nearcoord:` / `neartitle:` | `nearcoord:40km,9.97,76.28` (196 near Kochi) | `boost-nearcoord:` ranks instead of filtering |
| `creationdate:` / `lasteditdate:` | `creationdate:>=2026-01-01` (39 new medicine articles with cn) | Fresh and stale filters |
| `haswbstatement:` | `haswbstatement:P180=Q1800` (Commons) | Wikidata and Commons |
| `insource:/regex/` | — | Expensive; always pair with other filters |
| `boost-templates:` / `prefer-recent:` | — | Relevance-sort tuning |
| `srsort=` | `incoming_links_desc`, `last_edit_desc`, `create_timestamp_desc`, `random`, `user_random` | Ordering without extra calls |

### 5.3 MediaWiki REST API (`https://{wiki}/w/rest.php/v1/…`)
| Endpoint | Status |
|---|---|
| `page/{t}/bare` (latest revision, license) | ✅ |
| `page/{t}/html` (Parsoid HTML) | ✅ |
| `page/{t}/history/counts/edits` | ✅ Koomapatti: 55 edits |
| `page/{t}/links/language` | ✅ |
| `search/page?q=` | ✅ |
| `/api/rest_v1/*` (RESTBase) | ⚠️ being retired; plan to migrate |

### 5.4 Analytics (`https://wikimedia.org/api/rest_v1/metrics/…`) ✅
- `pageviews/per-article/{project}/all-access/user/{title}/daily/{start}/{end}` gives impact (Kerala ≈ 3,185/day).
- **`pageviews/top-per-country/IN/all-access/2026/10/11`** gives what readers *in a country* read (Drishyam: The Conclusion, Neha Bora…). This is regional trending.
- `pageviews/top/ml.wikipedia/…` gives per-wiki trending.
- `pageviews/top-by-country/ml.wikipedia/…` gives where a wiki's readers are.
- `edits/per-page/…`, `editors/by-country/…` give activity data.

### 5.5 Citoid ✅ (`/api/rest_v1/data/citation/mediawiki/{DOI|PMID|PMC|URL|ISBN}`)
Turns an identifier into full citation metadata. Examples: DOI `10.1056/NEJMoa2034577` → NEJM 2020, vol 383(27), pp 2603–2615; the WHO TB fact sheet URL → `webpage` item; `PMC7745181` → journal article with MeSH tags. This is what VisualEditor's "Cite" button uses. **This is how Compass's references become paste-ready `{{cite journal}}`.** (It sits on the retiring RESTBase path, so watch for the move.)

### 5.6 Lift Wing ML (`POST https://api.wikimedia.org/service/lw/inference/v1/models/{model}:predict`) ✅
| Model | Body | Live result |
|---|---|---|
| `enwiki-articlequality` (and eu, fa, fr, gl, nl, pt, ru, sv, tr, uk) | `{"rev_id":1376786710}` | Koomapatti → **Stub** (0.675) |
| `outlink-topic-model` (**any language**) | `{"page_title":"കേരളം","lang":"ml"}` | South Asia 0.966 |
| `article-country` | `{"lang":"en","title":"Koomapatti"}` | India 1.0, with sources (P17, P625, links) |
| `revertrisk-language-agnostic` | `{"rev_id":…,"lang":"en"}` | 0.028 |
| `article-descriptions` | `{"lang":…,"title":…}` | ⚠️ 25 languages; **not ml**, but includes hi, gu, ne, si |

There is no public `inference.wikimedia.org` host; use `api.wikimedia.org`. Anonymous use is rate-limited, so register an API token for production.

### 5.7 Content Translation recommendations ✅ (`https://api.wikimedia.org/service/lw/recommendation/api/v1/…`)
- `translation?source=en&target=ml&seed=Kerala&count=5` → *LGBTQ rights in Kerala*, *Migrant labourers in Kerala*…
- `translation?…&topic=medicine-and-health` and `…&country=ind` filter by topic or country.
- **`translation/sections?source=en&target=ml&seed=Kerala`** returns **missing sections** in articles that already exist in both languages, with headings mapped. Example: *K. K. N. Kurup* has Awards/Works on mlwiki, but *Education* (വിദ്യാഭ്യാസം) and *Teaching* are missing.

This is the same engine as Content Translation's own suggestions, so Discover should call it instead of sampling categories alphabetically.

### 5.8 Toolforge and community APIs ✅
| API | Example | Gives |
|---|---|---|
| XTools `user/pages_count/{wiki}/{user}` | Netha Hussain enwiki: 374 live + 24 deleted, avg 2,148 bytes | Article creations (authoritative) |
| XTools `user/simple_editcount/ml.wikipedia.org/Ranjithsiji` | **4,300 creations on mlwiki**; sysop, bureaucrat | Home-wiki footprint and rights |
| XTools `page/articleinfo` | Koomapatti: creator Ranjithsiji, 55 revisions, 32 editors, 177 views/30 days | Article context |
| XTools `page/prose` | 76 words, 6 refs | Prose size |
| PetScan, Citation Hunt, Listeria | (not probed) | Category intersections; cn snippets; Wikidata-driven lists |

### 5.9 Events and real-time data ✅
- **CampaignEvents REST** (`/w/rest.php/campaignevents/v0/…`). Spec discovered at `/w/rest.php/specs/v0/module/campaignevents%2Fv0`. It has endpoints for:
  - `event_discovery/discoverable_events?page=<article>` (is this article on an active event's worklist?)
  - `participant/{userid}/event_registrations`
  - `event_registration/{id}/worklist_pages` (`…/quality`)
  - `worklist/{title}/pages`
- **EventStreams** (`https://stream.wikimedia.org/v2/stream/recentchange`, `mediawiki.page_change.v1`): a live server-sent-events feed of every edit on every wiki. Use it for "your article was just tagged or reverted" alerts.

---

## 6. Signals catalogue

### 6.1 Article signals (for ranking tasks)
| Signal | Source | Meaning for ranking |
|---|---|---|
| Topic scores | `cirrusdoc` `articletopic/*`; `outlink-topic-model` | Relevance to the user's topics |
| Country | `cirrusdoc` `articlecountry/*`; `article-country` | Relevance to the user's region |
| Coordinates | `cirrusdoc.coordinates`; Wikidata P625 | Local relevance via `nearcoord:` |
| Quality class | PageAssessments; Lift Wing `articlequality` | Stub/Start = high-leverage; GA/FA = avoid for newcomers |
| Importance | PageAssessments | Top/High = more readers benefit |
| Pageviews (30-day) | Analytics | Impact |
| `popularity_score`, `incoming_links` | `cirrusdoc` | Importance without a separate pageviews call |
| Sitelink count | Wikidata | Global importance; translation value |
| Watchers | `prop=info` | Many watchers = contested; few = neglected |
| Protection | `prop=info` | Exclude for newcomers |
| Size / prose words / ref count | `text_bytes`; XTools prose; Parsoid | Feasibility: small articles are 15-minute tasks |
| Uncited paragraphs, `{{cn}}` count and dates | Parsoid `data-mw` | Exact location and age of the problem |
| Banner tags and dates | Hidden tracking categories | Task type and age |
| Growth recommendations | `hasrecommendation:`; `cirrusdoc` `recommendation.*` | Machine-prepared, very low-effort tasks |
| Last edit / creation date | `cirrusdoc.timestamp`, `create_timestamp`; `lasteditdate:` | Neglected vs active |
| Revert risk of the latest revision | Lift Wing | Possible vandalism to fix |
| Event worklist membership | CampaignEvents | Join a live campaign |

### 6.2 User signals (for the profile)
| Signal | Source |
|---|---|
| Home wiki and footprint per wiki | `globaluserinfo` |
| Declared languages | `meta=babel` on the user's top wikis |
| Topics and countries | Aggregate `cirrusdoc` `weighted_tags` over edited articles (§9) |
| Place cluster | Coordinates of edited articles; P131 chains (existing `geo_service`) |
| Creations | `ucshow=new`; XTools `pages_count` |
| Edit style | Edit tags (`visualeditor`, `contenttranslation`, `shortdesc helper`…) and `sizediff` |
| Reliability | `mw-reverted` share (exclude self-reverts) |
| Rights | XTools `user_groups` (e.g. sysop, so admin backlogs are relevant) |
| Commons footprint | `allimages` + `globalusage` (unused uploads); SDC gaps |
| Wikidata footprint | `ucshow=new` on Wikidata; items missing labels or descriptions in their languages |
| Events joined | CampaignEvents `participant/{id}/event_registrations` |

---

## 7. Gotchas we hit

1. **`hastemplate:` is transitive.** It matches nested templates (*Lok Sabha* matches "Unreferenced"). Use tracking categories.
2. **`articlecountry:` uses ISO alpha-3 codes** (`ind`, `nga`, `zaf`); full names return 0.
3. **`morelike:` can't be combined** with filters; use `morelikethis:`.
4. **Batch with POST.** Non-Latin titles × 50 overflow GET URLs.
5. **Babel is per wiki.** Query the user's top wikis, not Meta.
6. **`mw-reverted` includes self-reverts.** Look up the reverting revision's author before calling an edit "reverted by others".
7. **Wikidata `claims[0]` is not the best value.** Respect `rank: preferred`, and skip P576 (dissolved) entities for geo.
8. **WDQS is slow, its data is imperfect, and the graph split happened in 2025.** Cache results, sanity-check them, and use the scholarly endpoint for papers.
9. **RESTBase (`/api/rest_v1/page/*`) is being retired.** Use `rest.php` and Action API equivalents. Citoid and Analytics stay on their own paths for now.
10. **ML coverage varies.** `articlequality` exists for 11 wikis (not ml), `article-descriptions` for 25 languages (not ml), and `hasrecommendation` types vary by wiki. Topic, country and outlink models are language-agnostic.
11. **Some Growth APIs need login** (`list=growthtasks`), and the watchlist needs OAuth. Design so they're optional.
12. **Semantic Scholar without a key returns 429** (see EVALUATION.md). Prefer Citoid and PubMed, or get a key.
13. **Etiquette:** Wikimedia's User-Agent policy requires contact info. Use `maxlag`, serial or low-concurrency requests, and cache aggressively.

---

## 8. Applying this to Compass

Each item names the current file, the new data source, and the user-visible result.

### 8.1 Profile v2 (`backend/services/profile_service.py`)
| Today | v2 |
|---|---|
| enwiki only | Home wiki from `globaluserinfo`; profile built on the top 1–2 content wikis, plus Commons and Wikidata footprints |
| 12-keyword `TOPIC_KW` over 50 articles | Aggregate `cirrusdoc` `articletopic` and `articlecountry` over 150–500 edited articles (§9: 7 s, correct for Hog Farm, Cwmhiraeth, Ranjithsiji on mlwiki) |
| Edit types from summary regexes | Edit tags (`contenttranslation`, `visualeditor`, `shortdesc helper`…) + `sizediff`; keep summaries as a fallback |
| Creations via "creat" in summaries (20 of 648 found) | `ucshow=new` on each wiki, or XTools `pages_count` |
| `qualityTier` = own revert rate | Remove, or replace with "reverted by others" via `mw-reverted` minus self-reverts |
| 20,000 contributions in 40 sequential calls | 500–2,000 contributions plus `cirrusdoc`; cache per user |
| Languages = any wiki with ≥ 10 edits | Babel (per wiki) ∪ wikis with ≥ 100 content edits; ignore `test*`, `abstractwiki` |

### 8.2 Tasks v2 (`backend/routes/tasks.py`, `backend/services/scoring_service.py`)
Build the candidate pool from several **precise** sources, all scoped to the user's home wiki:

| Source | Query recipe | Example |
|---|---|---|
| Topic + country maintenance | `incategory:"All articles lacking sources" articletopic:<t> articlecountry:<c>` | 912 unsourced Indian articles |
| User's own categories | `incategory:"<user's top category>"` + a tracking category | Malayalam film actors needing refs |
| Near the user's places | `nearcoord:40km,<lat>,<lon>` + a tracking category | 196 near Kochi |
| Similar to the user's best articles | `morelikethis:"<their article>"` + a tracking category | Cardiology for *Lake Louise criteria* |
| Growth structured tasks | `hasrecommendation:link\|image` + topic or country | 17k mlwiki "add a link" |
| WikiProject pools | `list=projectpages` (e.g. Medicine, India) filtered to Stub/Start, High/Top | Community-prioritised |
| Recent problems | `incategory:"Articles with unsourced statements from <this month>"` + topic | Fresh `{{cn}}` |
| Small-wiki reports | `list=querypage` Lonelypages / Deadendpages | mlwiki orphans |

**Ranking.** Replace keyword weights with real signals, all available from one `cirrusdoc` batch plus a pageviews call:
```
score = 0.30·topic_match          (cosine of user topic vector vs article articletopic scores)
      + 0.20·place_match          (articlecountry match, or distance to user's place cluster)
      + 0.15·impact               (log pageviews or popularity_score; importance class)
      + 0.15·feasibility          (small text_bytes, Stub/Start/C class, inline tag vs banner, not protected)
      + 0.10·freshness            (recent tag date, or "tagged after your last edit")
      + 0.10·affinity             (task type matches user's edit-tag history)
```
**Every card states its reason**, for example: "Because you edited 12 Malayalam film articles · 3 `{{cn}}` in *Career* since 2024 · 900 views/day · Start class".

### 8.3 Revisit v2 (`backend/services/watchlist_service.py`)
- Run on **every wiki** the user creates articles on (Ranjithsiji: 4,300 mlwiki creations).
- Use **dated** tracking categories, and compare each tag's date with the user's last revision (`prop=revisions&rvuser=`). Highlight "new since you last edited".
- Fix the labels: "Needs more references" ≠ "Unreferenced".
- Add machine signals: `hasrecommendation:image` on their own articles, a missing short description, Lift Wing quality `Stub`, and a high revert-risk latest edit (possible vandalism on their article).
- Optional live alerts through **EventStreams**: "Your article *Koomapatti* was just tagged {{cn}}."

### 8.4 Discover v2 (`backend/routes/discover.py`)
- Use the **Content Translation recommendation API** (`translation?seed=<their article>&source=en&target=<home lang>`) instead of alphabetical category sampling. Use **`translation/sections`** for missing sections in articles that already exist in both languages.
- Add WDQS gap lists, precomputed and cached: "places in your district missing in Malayalam", "women in your field missing in Malayalam".
- Rank by sitelink count and source pageviews; restrict to Babel languages.
- Link to `Special:ContentTranslation?page=<title>&from=en&to=<lang>`.
- **Monolingual editors:** reverse the direction (e.g. important articles in hi, ta, fr or de with no English article), or use `Wantedpages` red links in their topics.

### 8.5 Article Guide v2 (`backend/services/article_service.py`)
- Parse **Parsoid HTML** instead of regexes over wikitext. List:
  - each **uncited paragraph**, with section and first words ("*Early life*: 'Venu was born as K. Venugopal…'")
  - each inline tag with its date
  - dead links
  - bare-URL refs
  - lead length
  - infobox presence
- Compare the infobox with Wikidata, e.g. a birth date present on Wikidata but missing in the article.
- **Images:** if Wikidata P18 or the P373 Commons category has photos and the article has none, show thumbnails with a one-click "use this image".
- **Missing sections:** use `translation/sections` mappings and section frequency in same-class articles of the same type. Drop the fixed templates ("Add 'Description' section").
- Show the quality class (PageAssessments or Lift Wing) and what the next class requires.

### 8.6 References v2
- **Delete** the "Wikipedia articles as references" list (WP:CIRCULAR).
- Choose sources by **topic, not title words**. If `articletopic` includes Medicine & Health, query PubMed (so *Tuberculosis* and *Lake Louise criteria* both qualify). Use CrossRef and OpenAlex for STEM, and Google Books or Open Library ISBNs for history and biography.
- Convert every result with **Citoid** into a ready-to-paste `{{cite journal}}`/`{{cite web}}`.
- Remove sources the article already cites (DOIs and URLs from Parsoid refs).
- Reuse Wikidata references (P248/P854) on the article's item.

### 8.7 Trends v2 (`backend/services/trends_service.py`)
- Replace global top-50 with **`top-per-country/<user country>`** (verified for IN) and **`top/<home wiki>`**.
- Keep only trending articles that **need work** (tracking categories, Stub/Start class, `hasrecommendation`). The output becomes "Readers in India are reading *X* today, and it has 4 `{{cn}}` tags."
- Drop the dead `Category:Ongoing_events` source and the DYK scraping.

### 8.8 New features unlocked
| Feature | Built from | Who it serves |
|---|---|---|
| **Place your photos** | Commons `allimages` + `globalusage` + matching articles (P18 empty, `nearcoord:`) | Ranjithsiji, Netha Hussain (Commons-heavy) |
| **Add "depicts" to your uploads** | SDC P180 gaps | Commons contributors |
| **Wikidata gaps in your language** | WDQS: items in your area/topic missing labels or descriptions in `ml` | Athulvis (222k Wikidata edits, 46 enwiki) |
| **Join a campaign** | CampaignEvents `discoverable_events` / worklists | Event participants |
| **Live alerts** | EventStreams filtered to the user's articles | Article creators |
| **Newcomer mode** | `hasrecommendation:link\|image`, small Stub/Start articles, no protected pages, link to `Special:Homepage` | New editors |
| **Admin backlogs** | User rights (XTools) → relevant `querypage` and backlog categories | Sysops like Ranjithsiji on mlwiki |

### 8.9 Architecture changes
1. **Wiki-agnostic client:** one module, parameterised by `dbname`, with UA, `maxlag`, retries, POST batching and per-host concurrency limits. It replaces Compass's three HTTP clients.
2. **Signal cache:** a per-article cache of `cirrusdoc` + assessments + pageviews (TTL ~24 h) and a per-user profile cache (TTL ~6 h). Fill the WDQS gap lists with a nightly batch job.
3. **Progressive API:** return the profile within 5 s using `cirrusdoc`, then stream task sources as they finish. Mark partial failures (`partial: true`).
4. **Optional OAuth 2.0** (Meta OAuth consumer) for watchlist-based Revisit and logged-in Growth tasks. Read-only works without it.
5. **Host on Toolforge** to stay close to Wikimedia APIs and the community.

---

## 9. Proof of concept: ML-tag profiles

I aggregated `cirrusdoc` `weighted_tags` over each user's last 150 edited articles. That's 3 batched calls per user, about 7 s:

| Editor | Compass today (`TOPIC_KW`) | From Wikipedia's own ML tags | Correct? |
|---|---|---|---|
| Hog Farm | biography, history, education | **Military & warfare** 79 · North America 63 · Transportation 31 · country **United States** 107 | ✅ American Civil War, railroads |
| Cwmhiraeth | biography, culture, history | **STEM.Biology** 24 (top) · North America 21 · Sports 17 | ✅ biology leads |
| Netha Hussain (enwiki) | biography, india, medicine | South Asia 89 · **Food & drink** 43 · country **India** 95 | ✅ for her recent work (Kerala cuisine). Medicine is older; use a longer window or decay weighting. |
| Ranjithsiji (**mlwiki**) | *(cannot see mlwiki)* | South Asia 92 · **Films** 22 · Religion 10 · Food 7 · country India 104 | ✅ Malayalam cinema, Kerala |

This one change replaces `TOPIC_KW`, `GEO_KW`, `extract_topics()` and `extract_geo()`, and works on every Wikipedia language.

---

## 10. Roadmap

| Phase | Work | Key APIs | Expected effect (eval rubric) |
|---|---|---|---|
| **1. Precision** (1–2 weeks) | Profile from `cirrusdoc`; tasks from tracking categories + `articletopic` / `articlecountry` / `nearcoord` / `morelikethis`; signal-based ranking with reasons; `mw-reverted`; `ucshow=new`; fix labels and links | Action API, CirrusSearch | Tasks 2 → ~6; Profile 3 → ~6 |
| **2. Multi-wiki** (2–4 weeks) | Home wiki and Babel; template mapping via Wikidata; Revisit and Tasks on mlwiki/tawiki/…; `querypage` reports | globaluserinfo, langlinks, querypage | Coverage up across all features; overall ~6 |
| **3. Cross-project** (3–4 weeks) | CX recommendation API + `sections`; WDQS gap lists (cached); Commons "place your photos"; Wikidata label and description gaps | Lift Wing recommendation, WDQS, Commons | Discover 5 → ~8; new features for Commons and Wikidata editors |
| **4. Depth** (3–4 weeks) | Parsoid paragraph-level Guide; Citoid citations; topic-routed references; regional Trends | Parsoid, Citoid, PubMed, pageviews top-per-country | Guide 3 → ~7; References 3 → ~7; Trends 2 → ~6 |
| **5. Engagement** | EventStreams alerts; CampaignEvents; OAuth watchlist; newcomer mode; Toolforge hosting; feedback loop | EventStreams, CampaignEvents, OAuth | Habitual use |

After each phase, re-run `eval/` and compare with `eval/baseline/2026-10-13-metrics.json`.

---

## 11. Sources

Documentation consulted (2026-10-13). Everything else above was verified by live API calls.
- [Help:CirrusSearch](https://www.mediawiki.org/wiki/Help:CirrusSearch): search keywords, `articletopic`, `articlecountry`, `hasrecommendation`, `morelikethis`, geo search, sort orders, limits
- [Machine Learning/LiftWing](https://wikitech.wikimedia.org/wiki/Machine_Learning/LiftWing): current inference services
- [Machine Learning/LiftWing/Usage](https://wikitech.wikimedia.org/wiki/Machine_Learning/LiftWing/Usage)
- [RESTBase](https://www.mediawiki.org/wiki/RESTBase) and [RESTBase/deprecation](https://www.mediawiki.org/wiki/RESTBase/deprecation)
- [Wikimedia APIs/Changelog](https://www.mediawiki.org/wiki/Wikimedia_APIs/Changelog)
- [WikiCite/WDQS graph split](https://meta.wikimedia.org/wiki/WikiCite/WDQS_graph_split)
- [Recommendation API](https://meta.wikimedia.org/wiki/Recommendation_API)
- [Extension:GrowthExperiments](https://www.mediawiki.org/wiki/Extension:GrowthExperiments)
- [Extension:CampaignEvents](https://www.mediawiki.org/wiki/Extension:CampaignEvents)
- [Phabricator T293648](https://phabricator.wikimedia.org/T293648): CX recommendations API requirements
