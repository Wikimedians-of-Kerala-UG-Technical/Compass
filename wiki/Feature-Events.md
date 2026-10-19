# Feature: Events

**Endpoints:** `/api/events…` (see [[API-Reference#events]])
**Service:** `services/event_service.py`
**UI:** `/event` and `/event/<id>?user=<User_name>` (linked from the start screen and from Commons & Wikidata)

Answers: *at this edit-a-thon, which of the worklist's articles suit me best?*

---

## Why it builds on Event Registration

Wikimedia's own **Event Registration** tool (the CampaignEvents extension, on every wiki) already runs edit-a-thons: signup, a **worklist** of articles to work on, contribution tracking and a goal bar. Compass doesn't copy any of that. Every participant there sees the same worklist; Compass orders it for each one. Organisers keep using the official tool, and edits still count on the event page.

## Finding the event

`/api/events/resolve?ref=` accepts what an organiser would share:

| Input | Resolved how |
|---|---|
| `4579` | The ID itself |
| `…/wiki/Special:EventDetails/4579` (any wiki, any language) | The number after `EventDetails/` |
| `Event:Name` or its URL | The event page's HTML carries `wgCampaignEventsEventID` |

## What is read

| Data | Source |
|---|---|
| Event (name, dates, wikis, goal) | `GET meta.wikimedia.org/w/rest.php/campaignevents/v0/event_registration/{id}` (IDs are global) |
| Worklist | The JSON page `<event page>/Worklist`, read with `action=raw`: `{"enwiki": ["Title", …], …}` |
| Participants | `GET …/event_registration/{id}/participants?include_private=false`, paged, up to 200 (public registrations only) |

Cached for 10 minutes.

## Ranking

`/api/events/<id>/rank/<username>` ranks the worklist's articles on one wiki: the editor's home wiki when the worklist has it, else the wiki with the most worklist articles (or `?wiki=`). The editor's profile is built on that wiki when they edit there, else on their home wiki; topics and countries are the same taxonomy everywhere, so it still ranks.

Each article (up to 1,000) is read through `cirrusdoc` and scored:

```
score = 0.45 topic + 0.25 place + 0.15 feasibility + 0.15 affinity
      + 0.05 × urgency of its most urgent maintenance tag
      + 0.10 if the editor has edited it before
```

- **topic**: cosine between the editor's topic shares and the article's ML topics;
- **place**: 1.0 / 0.7 / 0.5 / 0.4 when the article is about the editor's 1st / 2nd / 3rd / 4th country;
- **feasibility**: by size, as in Tasks (small and Stub/Start/C-class articles score higher);
- **affinity**: how much of the editor's work is the kind of edit the article needs (citations, linking, expanding).

Short articles with no maintenance tag are shown as "expand" tasks, since that is usually why an organiser listed them. Worklist titles that don't exist yet are listed separately under "Not written yet" with a create link. The top 100 are returned. Cached for 30 minutes.
