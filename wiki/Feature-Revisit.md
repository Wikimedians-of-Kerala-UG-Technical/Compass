# Feature: Revisit

**Endpoint:** `GET /api/revisit/<username>[?wiki=]`
**Service:** `services/revisit_service.py`
**UI:** Revisit

Answers: *which of my own articles need me again?* The editor already knows these articles, so they can act on them at almost no cost.

---

## Which articles

The editor's 50 most recent **creations** (`ucshow=new`, so exact) plus their 15 most-edited articles (3+ edits), all on the home wiki. The backend reads them from the cached profile, so the frontend no longer sends the lists as JSON.

## What is checked

| Check | Source | Tag |
|---|---|---|
| Maintenance tags | Tracking categories (enwiki) or local templates, via `maintenance.issues_of` | e.g. "Citation needed · 2026-07" |
| Tag date | Dated hidden category, e.g. "Articles needing additional references from July 2025" | `since: "2025-07"` |
| New since your last edit | Tag month later than the month of the editor's last edit on the page (from contributions) | `newSinceYourEdit: true`, plus a "New since your last edit" badge |
| Suspicious latest edit | Latest revision (`prop=revisions`) is by someone else, and Lift Wing `revertrisk-language-agnostic` ≥ 0.9 | "Check latest edit", with a link to the diff |
| Growth suggestions | `cirrusdoc` `recommendation.link` / `recommendation.image` | "Suggested links" / "Suggested image" |
| Short description (enwiki) | Not in "Articles with short description" | "No short description" |

**Labels are exact.** v1 showed "Needs more references" as "Unreferenced". Now each tracking category maps to its own label (`add_refs` = Unreferenced, `more_refs` = Needs more references, `inline_cites` = No inline citations, and so on).

## Order

1. Items with something new since the editor's last edit.
2. Items with a real problem.
3. "Weak" items: only a stub tag or a link suggestion.

Within each group, items with more tags come first.

## Multi-wiki

Pass `?wiki=` (or switch wiki on the Overview) to check another Wikipedia. Ranjithsiji's mlwiki creations now get checked; v1 only looked at enwiki.
