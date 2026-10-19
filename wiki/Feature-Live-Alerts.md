# Feature: Live alerts

**Endpoint:** `GET /api/alerts/<username>/stream` (server-sent events)
**Service:** `services/alerts_service.py`
**UI:** the bell in the top bar; "Live on your articles" on Overview; browser notifications

Answers: *has someone just edited or tagged one of my articles?*

Only on your own dashboard, logged in with your Wikimedia account: a live feed of someone else's articles would read as monitoring them. The bell is hidden on other people's dashboards, and the stream returns `403`.

---

## How it works

1. The browser opens an `EventSource` to the stream endpoint. The backend builds the editor's watch set: articles they created, heavily edited, or edited among their last 200, plus their watchlist when they're logged in.
2. `AlertHub` keeps **one** connection to Wikimedia's public `recentchange` stream (all wikis, ~50 events a second) for as long as anyone is subscribed, and reconnects with `Last-Event-ID` if it drops.
3. Each event is matched by `(wiki, title)`:
   - `edit` / `new` in the main namespace by someone other than the editor → an **edit** alert with a diff link.
   - `categorize` on a tracking category (the same localized ones Tasks uses, e.g. "All articles lacking sources") → the comment's first link names the article. The added/removed wording is translated per wiki, so the article's current categories are re-read to decide between **tagged** and **untagged**.
4. Alerts go to each subscriber's queue (100 max; a stalled tab drops old alerts, not the stream) and out as `alert` events. A comment every 25 s keeps proxies from closing the connection.

The browser shows a notification only when the tab is in the background and permission was granted.

## Limits

- One server thread per open tab: run gunicorn with threads (the shipped config does).
- `mw-reverted` isn't in `recentchange`, so "your edit was reverted" isn't an alert.
- No email digest or service worker; alerts arrive only while a Compass tab is open.
