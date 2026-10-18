# Feature: Commons & Wikidata

**Endpoint:** `GET /api/contribute/<username>[?wiki=&place=&placeName=]`
**Service:** `services/crossproject_service.py`
**UI:** Commons & Wikidata

Answers: *what can a photographer or Wikidata editor do next?* Many of the editors Compass serves do most of their work on Commons and Wikidata, not in articles.

---

## Place your photos

1. The editor's 50 most recent Commons uploads (`list=allimages&aiuser=`).
2. `prop=globalusage&gunamespace=0` drops every file already used in an article on any wiki. SVGs (logos, diagrams) are skipped.
3. For each unused photo, it suggests candidate articles on the home wiki:
   - if the file has coordinates: `nearcoord:1km,<lat>,<lon>`;
   - otherwise: a search on the cleaned file name (camera prefixes, timestamps and extensions removed).

Example (October 2026): 20 of Ranjithsiji's last 50 uploads were unused. Several photos of the Inchathotty Suspension Bridge matched the mlwiki article ഇഞ്ചത്തൊട്ടി തൂക്കുപാലം.

## Wikidata gaps

A WDQS query for items located (P131, any depth) in the editor's focus place (`focus.local`, else `focus.region`) with **no description in the home language**. It also flags those with no label. Items are ordered by sitelink count, so the best-known items come first.

Example: Ernakulam district → St. Francis Church, Santa Cruz Basilica, Jawaharlal Nehru International Stadium and Kalamassery, all without a Malayalam description.

## Campaigns

`/w/rest.php/campaignevents/v0/event_discovery/discoverable_events?page=<title>` for the editor's 10 most-edited articles. It lists active events (CampaignEvents extension) whose worklists include them. Each one links to [[Feature-Events]], which ranks that event's worklist for the editor.

The endpoint only answers for a logged-in Wikimedia user: for an anonymous request (which is what Compass's server sends) it returns `[]`, so this list is currently always empty.
