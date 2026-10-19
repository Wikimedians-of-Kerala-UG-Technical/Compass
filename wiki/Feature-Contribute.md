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

Upcoming and ongoing events (Event Registration) whose worklist includes any article the editor created, edited a lot or edited recently on their home wiki. Each card shows the dates, links to the event page, and links to [[Feature-Events]], which ranks that event's worklist for the editor.

The extension's own lookup (`event_discovery/discoverable_events`) only answers logged-in users and returns `[]` to anonymous requests, so Compass reads the worklists itself:

1. Search Meta's Event namespace (1728) for `intitle:Worklist`, keeping pages whose content model is `worklist` (some ".../Worklist" pages are ordinary wikitext).
2. Read them all (one batched request per 50) into an index `{dbname: {title: [event pages]}}`, cached for 30 minutes and shared by every user. In October 2026 that is 53 worklists and about 6,000 articles, built in about 2.5 s.
3. Look up the editor's titles in the index, then resolve each matching event page to its event and drop test events and events that ended more than a day ago.

Worklists whose event page lives on a wiki other than Meta aren't indexed.
