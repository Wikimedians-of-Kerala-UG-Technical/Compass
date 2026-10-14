# Feature: Geographic Focus

**Endpoint:** `GET /api/geo/<username>[?wiki=]`
**Service:** `services/geo_service.py`
**UI:** Overview ("Where you edit"); feeds Tasks (near you), Discover (missing near you) and Commons & Wikidata (gaps)

Answers: *which places does this editor write about?*

---

## How it works

1. Map the editor's ~200 profile articles to Wikidata items (`prop=pageprops&ppprop=wikibase_item`, on the home wiki).
2. Read each item's claims (`wbgetentities`, 50 per call over POST, labels in the home language with English fallback).
3. Pick where to start walking up the hierarchy:
   - **People** start at their birthplace (P19), else their citizenship (P27).
   - **Countries and first-level divisions** start at themselves.
   - **Anything else in a hierarchy (P131)** starts at itself. It counts its *own* label only when it's a populated place (has P1082 population), so "Kerala Soil Museum" contributes Ernakulam and Kerala but not itself.
4. Walk P131 ("located in"), falling back to P17 (country), up to 6 levels. Each level is fetched for all articles in one batch.
5. Count every level. Skip **dissolved** entities (P576), so "Kingdom of Great Britain" and "Russian Empire" no longer become someone's focus.

Statements are read **by rank**: preferred first, deprecated ignored. v1 took `claims[0]`, which often landed on historical values.

## Focus

| Field | Rule |
|---|---|
| `focus.region` | The most-counted first-level division (state/province) with ≥ max(2, 5% of geo-tagged articles); else the top sub-national place |
| `focus.local` | The most-counted district/city *inside that region* that has coordinates (P625) and ≥ 2 articles |
| `focus.country` | The most-counted country |

v1 picked "the first place that isn't a top-3 country", ignoring counts. That gave Titodutta (India: 86 articles) a focus of *Kamikawa Subprefecture, Hokkaido* (10), and Doc James *Kentucky* (2 of 2,633).

Example: Ranjithsiji (mlwiki) → region കേരളം (Kerala, 58), local എറണാകുളം ജില്ല (Ernakulam district, 12), country ഇന്ത്യ.

## Where it's used

- **Tasks:** `nearcoord:25km,<local coord>` + maintenance filter.
- **Discover:** items located directly in `local` or `region` that have an English article but none in the editor's language.
- **Commons & Wikidata:** items in `local` (any depth) missing a description in the editor's language.

Results are cached 6 h per (wiki, article set); claims are cached 7 days.
