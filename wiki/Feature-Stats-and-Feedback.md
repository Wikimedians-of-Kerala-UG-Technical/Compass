# Feature: Stats and task feedback

**Endpoints:** `GET /api/stats/<username>`, `POST /api/feedback`, `GET /api/feedback/<username>`
**Services:** `services/stats_service.py`, `services/feedback_service.py`
**UI:** "Your stats" view; the four vote buttons on every Tasks card

---

## Stats

Read from the editor's **live** contributions on the wiki (last 90 days, up to 5,000 edits), not from the 6-hour profile cache, and cached for an hour.

| Number | How |
|---|---|
| Day streak | Consecutive UTC days with an edit, ending today or yesterday (today isn't over) |
| Longest in 90 days | Longest run of such days in the window |
| Edits, articles, kB added (30 days) | From the contributions; kB counts positive `sizediff` only |
| Readers this month | 30 days of human page views (`agent=user`) for up to 25 articles edited in the last 30 days |
| Calendar | Edits per day for 90 days, one hue at four strengths, with a tooltip per day |
| Compass tasks | Liked, marked done, and edited after the editor saw them |

## Feedback

Each Tasks card has four buttons: 👍 **good suggestion** (`up`), ✓ **I did this** (`done`), 👎 **not for me** (`down`) and ⊘ **hide** (`dismiss`). Their tooltips say what each one does to the list and to what Compass learns. Everything except `up` removes the card from that editor's list on that wiki, now and on later visits; the server filters them out of `/api/tasks` and reports how many in `hidden`.

### Undo

Every vote can be taken back:

- **Click the highlighted button again.** The tooltip of a vote that's on ends with "(click again to undo)".
- **The Undo bar.** When a card disappears, a bar ("“Roti”: Not for you. Undo") stays for 8 seconds.
- **The hidden list.** "N tasks you finished, said aren't for you, or hid are not shown. Show them" lists every hidden task with why, and a **Restore** button.

Undo calls `DELETE /api/feedback/<username>?wiki=&title=`, which deletes every row for that article, so a vote taken back never counts in stats or in the weight fitting. `/api/tasks` returns the tasks it held back as `hiddenTasks`, so a restored task comes back with its full card.

### What is stored

Every vote is stored with the card's six ranking signals (topic, place, impact, feasibility, freshness, affinity) and score. When the editor's feedback is next read, Compass checks their contributions since each vote (60-day window) and records `edited_at` on votes whose article they then edited. That is the strongest signal: they acted on it.

### Learning the weights

```bash
python eval/learn_weights.py --db backend/.data/compass.db
```

Fits a logistic regression (positives: `up`, `done` or edited; negatives: `down`, `dismiss`), holds out 20% to compare accuracy with the current weights, and prints the fitted weights rescaled to the same total as `WEIGHTS` in `task_service.py`. It changes nothing by itself and refuses to run on fewer than 100 mixed rows.

Votes need no login, so anyone can vote on any editor's tasks. Use the fitted weights as a hypothesis, and confirm them with the evaluation in `eval/README.md`.
