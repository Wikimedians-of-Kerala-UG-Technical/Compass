"""Human-readable digest of one user's harness output — what you read when judging relevance.

Usage:
  python eval/digest.py eval/runs/2026-10-13 "Netha Hussain" [more users...]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import safe_dirname  # noqa: E402


def digest(run, user, n=12):
    d = os.path.join(run, safe_dirname(user))

    def L(name):
        p = os.path.join(d, f'{name}.json')
        return json.load(open(p)) if os.path.exists(p) else {}

    p, g, t = L('profile'), L('geo'), L('_timing')
    print(f'\n######## {user}')
    if 'error' in p:
        print('PROFILE ERROR', p['error'])
        return
    print('PROFILE', p.get('homeWiki', 'enwiki'), '| total', p['total'], '| unique', p['uniqueArticles'],
          '| topics', [(x['label'], x['share']) for x in p.get('topics', [])] or p['topTopics'],
          '| countries', [c['name'] for c in p.get('countries', [])],
          '| created', p.get('createdCount', len(p['createdArticles'])), '| reverted', p.get('reverted'))
    print('  top categories', [c['name'] for c in p.get('topCategories', [])[:6]])
    print('  edit types', sorted(p['editTypes'].items(), key=lambda kv: -kv[1])[:6])
    print('  heavily edited', [h['title'] for h in p['heavilyEdited'][:8]])
    print('GEO', g.get('articlesWithGeo'), [(x['name'], x['count']) for x in g.get('topPlaces', [])[:8]], '| focus ->', t.get('geoFocus'))
    tasks = L('tasks2') or L('tasks1') or []
    if isinstance(tasks, dict):
        tasks = tasks.get('tasks') or []
    print(f'TASKS ({len(tasks)}) — score | type | title | pageviews | reason | details')
    for x in tasks[:n]:
        print(f"   {x['score']} | {x['type']} | {x['title']} | {x['pageviews']} | {x.get('reason')} | {x.get('details')}")
    rv = L('revisit').get('tasks', [])
    print(f'REVISIT ({len(rv)})')
    for x in rv[:n]:
        print('   ', x['title'], [(tg['label'], tg.get('since')) for tg in x['tags']], 'NEW' if x.get('hasNew') else '')
    disc = L('discover')
    print('DISCOVER pairs', disc.get('pairs'), '| monolingual', disc.get('monolingual'), '| articles', len(disc.get('articles', [])),
          '| sections', len(disc.get('sections', [])), '| region gaps', len(disc.get('regionGaps', [])))
    for a in disc.get('articles', [])[:6]:
        print('   ', a['title'], '->', a['target'], '|', a['why'], '|', a['languages'], 'langs')
    for a in disc.get('sections', [])[:3]:
        print('    S', a['sourceTitle'], [m['section'] for m in a['missing']])
    c = L('contribute')
    print('CONTRIBUTE unused photos', len((c.get('commons') or {}).get('unused', [])), 'of', (c.get('commons') or {}).get('uploads'),
          '| wikidata gaps', len((c.get('wikidata') or {}).get('items', [])), 'in', (c.get('wikidata') or {}).get('place'))


if __name__ == '__main__':
    run = sys.argv[1]
    for u in sys.argv[2:]:
        digest(run, u)
