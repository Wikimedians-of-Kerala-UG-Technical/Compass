# Privacy

The same statements are shown to users at `/privacy` (`frontend/src/components/PrivacyView.vue`, text in `locales/en.json` → `privacy`). Keep both in step with the code.

## Public view and the owner

| Who | Sees | Can |
|---|---|---|
| Anyone, no login | Any editor's dashboard, built from public data | Vote in their own browser only |
| The editor, logged in | Their dashboard, plus their watchlist and Special:Homepage choices | Vote (stored, private), live alerts |
| Someone else, logged in | The public view | Same as no login |

`routes/auth.py`: `is_owner()` / `require_owner()`. The frontend uses `store.isSelf`.

## What is stored on the server

- Votes by the logged-in owner (`feedback` table): username, wiki, article, vote, ranking signals. Undo deletes them.
- Login sessions (`sessions` table): access and refresh tokens, 30 days at most; deleted on logout.
- Caches of public data (`COMPASS_CACHE_PATH`), hours at most.
- Request logs (gunicorn access log), including IP addresses.

No analytics, ads, trackers, or third-party fonts and scripts. The frontend loads nothing outside the Compass server; all data comes from Wikimedia APIs, called by the backend.

## Opt-out

An editor who creates `User:<name>/Compass-opt-out` on Meta (any content) gets no dashboard: every per-user endpoint returns `403` with a message naming the page (`profile_service.check_opt_out`, cached 10 minutes). Deleting the page opts back in.
