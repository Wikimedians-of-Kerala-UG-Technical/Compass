"""Fit the task-ranking weights to real feedback.

Usage:
  python eval/learn_weights.py                          # reads backend/.data/compass.db
  python eval/learn_weights.py --db /data/compass.db --min-rows 200

Every Tasks card carries the six ranking signals it was scored with (topic, place,
impact, feasibility, freshness, affinity). When an editor votes a card up, marks it
done or edits the article afterwards, that is a positive; a vote down or a dismissal is
a negative (see backend/services/feedback_service.py). This fits a logistic regression
on those signals and prints the weights rescaled to the same total (0.90) as the
hand-set WEIGHTS in task_service.py, so the two can be compared side by side.

It doesn't change any code. Apply new weights by hand, then re-run the evaluation
(eval/README.md) to check that relevance went up, not just agreement with the votes.
"""
import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.task_service import WEIGHTS as CURRENT  # noqa: E402

KEYS = list(CURRENT)


def fit(rows, epochs=400, lr=0.5, l2=1e-3, seed=0):
    """Plain logistic regression by gradient descent (no numpy needed for a few thousand rows)."""
    w = {k: 0.0 for k in KEYS}
    b = 0.0
    rng = random.Random(seed)
    data = list(rows)
    for _ in range(epochs):
        rng.shuffle(data)
        gw = {k: 0.0 for k in KEYS}
        gb = 0.0
        for x, y in data:
            z = b + sum(w[k] * x[k] for k in KEYS)
            p = 1 / (1 + math.exp(-max(min(z, 30), -30)))
            err = p - y
            for k in KEYS:
                gw[k] += err * x[k]
            gb += err
        n = len(data)
        for k in KEYS:
            w[k] -= lr * (gw[k] / n + l2 * w[k])
        b -= lr * gb / n
    return w, b


def accuracy(rows, w, b):
    hits = sum((b + sum(w[k] * x[k] for k in KEYS) > 0) == bool(y) for x, y in rows)
    return hits / len(rows) if rows else 0.0


def rescale(w, total=sum(CURRENT.values())):
    """Negative weights become 0 (a signal can't count against a task here)."""
    pos = {k: max(v, 0.0) for k, v in w.items()}
    s = sum(pos.values()) or 1.0
    return {k: round(v / s * total, 3) for k, v in pos.items()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--db', help='path to compass.db (default: COMPASS_DB_PATH or backend/.data/compass.db)')
    parser.add_argument('--min-rows', type=int, default=100, help='refuse to fit on fewer rows than this')
    args = parser.parse_args(argv)
    if args.db:
        os.environ['COMPASS_DB_PATH'] = args.db
    from services import feedback_service
    rows = feedback_service.training_rows()
    positives = sum(y for _, y in rows)
    print(f'{len(rows)} feedback rows with signals: {positives} positive, {len(rows) - positives} negative')
    if len(rows) < args.min_rows or positives in (0, len(rows)):
        print(f'Not enough (or one-sided) feedback to fit yet; need at least {args.min_rows} mixed rows.')
        return 1
    split = int(len(rows) * 0.8)
    random.Random(1).shuffle(rows)
    train, test = rows[:split], rows[split:]
    w, b = fit(train)
    cur_b = -sum(CURRENT.values()) / 2  # the hand-set weights, thresholded at their midpoint
    print(f'held-out accuracy: fitted {accuracy(test, w, b):.2f} vs current weights {accuracy(test, CURRENT, cur_b):.2f}')
    print(f'{"signal":<12} {"current":>8} {"fitted":>8}')
    for k, v in rescale(w).items():
        print(f'{k:<12} {CURRENT[k]:>8.2f} {v:>8.3f}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
