"""Compute the automated cohort metrics from a harness run.

Usage:
  python eval/metrics.py eval/runs/2026-10-13              # prints tables
  python eval/metrics.py eval/runs/2026-10-13 --json eval/baseline/2026-10-13-metrics.json

Metric definitions (see eval/README.md §5 for how they feed the ratings):
  literalTop10    tasks in the top 10 whose title contains their own `topic` string (case-insensitive)
                  -> high = lexical keyword matching, not subject matching
  pv0Top10        top-10 tasks reporting pageviews == 0 -> enrichment gaps / misleading numbers
  sharedTop10     top-10 titles that also appear in at least one other user's top 10 -> lack of personalisation
  titlesIn3Plus   titles in >= 3 users' top 10 (cohort-level)
  revisit*        item count, and share whose tags are only weak (stub/expand; v2: `weak` flag)
  discoverEmpty   users receiving 0 Discover suggestions
  personalTop10   (v2) top-10 tasks found through the user's own categories, articles or place
                  (scope cat:/like:/near) rather than only their ML topic
  hugeTop10       top-10 tasks on articles over 100 kB (not a quick task)

Handles both the v1 API (tasks as a list, `qualityTier`, `suggestedArticles`) and the v2
API (tasks under `tasks`, `reverted`, `articles`), so old runs can still be re-measured.
"""
import argparse
import json
import os
import statistics
from collections import Counter


def load(run, user, name):
    p = os.path.join(run, user, f'{name}.json')
    return json.load(open(p)) if os.path.exists(p) else None


def main(run, json_out=None):
    users = sorted(u for u in os.listdir(run) if os.path.isdir(os.path.join(run, u)) and not u.startswith('_'))
    rows, top10 = [], {}
    revisit_total = revisit_weak = 0
    for u in users:
        profile = load(run, u, 'profile')
        timing = load(run, u, '_timing') or {}
        if not profile or 'error' in profile:
            rows.append({'user': u, 'error': (profile or {}).get('error', 'no profile')})
            continue
        tasks = load(run, u, 'tasks2') or load(run, u, 'tasks1') or []
        if isinstance(tasks, dict):
            tasks = tasks.get('tasks') or []
        top = tasks[:10]
        top10[u] = [t['title'] for t in top]
        revisit = (load(run, u, 'revisit') or {}).get('tasks', [])
        for t in revisit:
            revisit_total += 1
            if t.get('weak', {x['key'] for x in t['tags']} <= {'stub', 'expand'}):
                revisit_weak += 1
        disc = load(run, u, 'discover') or {}
        contrib = load(run, u, 'contribute') or {}
        reverted = profile.get('reverted') or {}
        rows.append({
            'user': u,
            'homeWiki': profile.get('homeWiki', 'enwiki'),
            'globalEdits': profile.get('total'),
            'enwikiUniqueArticles': profile.get('uniqueArticles'),
            'topTopics': profile.get('topTopics'),
            'qualityTier': profile.get('qualityTier', f"reverted {round(reverted.get('share', 0) * 100, 1)}%"),
            'createdDetected': profile.get('createdCount', len(profile.get('createdArticles', []))),
            'geoFocus': timing.get('geoFocus'),
            'tasks': len(tasks),
            'literalTop10': sum(1 for t in top if t.get('topic') and t['topic'].lower() in t['title'].lower()),
            'pv0Top10': sum(1 for t in top if not t.get('pageviews')),
            'personalTop10': sum(1 for t in top if str(t.get('scope', '')).startswith(('cat:', 'like:', 'near'))),
            'hugeTop10': sum(1 for t in top if (t.get('size') or 0) > 100000),
            'revisitItems': len(revisit),
            'discoverSuggestions': len(disc.get('articles', disc.get('suggestedArticles', []))),
            'discoverSections': len(disc.get('sections', [])),
            'discoverRegionGaps': len(disc.get('regionGaps', [])),
            'discoverLanguages': len(disc.get('pairs', disc.get('userWikis', []))),
            'monolingual': bool(disc.get('monolingual')),
            'unusedPhotos': len((contrib.get('commons') or {}).get('unused', [])),
            'wikidataGaps': len((contrib.get('wikidata') or {}).get('items', [])),
            'secs': {k: v['secs'] for k, v in timing.items() if isinstance(v, dict) and 'secs' in v},
            'statuses': {k: v['status'] for k, v in timing.items() if isinstance(v, dict) and 'status' in v},
        })

    seen = Counter(t for titles in top10.values() for t in set(titles))
    for r in rows:
        if r['user'] in top10:
            r['sharedTop10'] = sum(1 for t in top10[r['user']] if seen[t] >= 2)

    ok = [r for r in rows if 'error' not in r]

    def med(step):
        vals = [r['secs'][step] for r in ok if step in r['secs']]
        return (round(statistics.median(vals), 1), max(vals)) if vals else (None, None)

    cohort = {
        'users': len(rows),
        'errors': [r for r in rows if 'error' in r],
        'titlesIn3Plus': [(t, c) for t, c in seen.most_common() if c >= 3],
        'usersAllTop10Literal': sum(1 for r in ok if r['literalTop10'] == 10),
        'revisitItems': revisit_total,
        'revisitWeakShare': round(revisit_weak / revisit_total, 2) if revisit_total else None,
        'discoverEmpty': [r['user'] for r in ok if r['discoverSuggestions'] == 0],
        'personalTop10Mean': round(statistics.mean(r['personalTop10'] for r in ok), 1) if ok else None,
        'hugeTop10Total': sum(r['hugeTop10'] for r in ok),
        'pv0Top10Total': sum(r['pv0Top10'] for r in ok),
        'homeWikis': dict(Counter(r['homeWiki'] for r in ok)),
        'nonOkStatuses': [(r['user'], k, s) for r in ok for k, s in r['statuses'].items() if s != 200],
        'latency': {step: dict(zip(('median', 'max'), med(step))) for step in ['profile', 'trends', 'tasks1', 'revisit', 'geo', 'tasks2', 'discover', 'contribute']},
    }

    print('| User | Wiki | Topics | Tier | Geo focus | Literal/10 | pv0/10 | Shared/10 | Personal/10 | Revisit | Discover (pairs) | Photos/WD | Profile s |')
    print('|---|---|---|---|---|--:|--:|--:|--:|--:|---|---|--:|')
    for r in ok:
        print(f"| {r['user']} | {r['homeWiki']} | {', '.join(r['topTopics'])} | {r['qualityTier']} | {r['geoFocus']} | {r['literalTop10']} | "
              f"{r['pv0Top10']} | {r.get('sharedTop10', 0)} | {r['personalTop10']} | {r['revisitItems']} | "
              f"{r['discoverSuggestions']} ({r['discoverLanguages']}) | {r['unusedPhotos']}/{r['wikidataGaps']} | "
              f"{r['secs'].get('profile')} |")
    print('\nCohort:', json.dumps({k: v for k, v in cohort.items() if k != 'errors'}, indent=1, ensure_ascii=False))
    if cohort['errors']:
        print('ERRORS:', cohort['errors'])

    if json_out:
        os.makedirs(os.path.dirname(json_out), exist_ok=True)
        with open(json_out, 'w') as f:
            json.dump({'run': os.path.basename(os.path.normpath(run)), 'cohort': cohort, 'users': rows}, f, indent=1, ensure_ascii=False)
        print('wrote', json_out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('run')
    ap.add_argument('--json')
    a = ap.parse_args()
    main(a.run, a.json)
