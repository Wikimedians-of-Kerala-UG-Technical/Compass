"""Establish what each test user ACTUALLY does, independently of Compass.

Usage:
  python eval/ground_truth.py --out eval/runs/2026-10-13 "Ranjithsiji" "Doc James"

For each user: global edit count, per-wiki breakdown, English-Wikipedia share,
declared languages (Babel on Meta), and real enwiki article creations
(list=usercontribs&ucshow=new — the authoritative count Compass's profile should match).
Writes <out>/_ground_truth.json and prints a markdown table.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import api  # noqa: E402


def creations(username, host='en.wikipedia.org', cap=5000):
    n, cont = 0, {}
    while n < cap:
        d = api(host, action='query', list='usercontribs', ucuser=username, ucshow='new',
                ucnamespace=0, uclimit=500, **cont)
        n += len(d['query']['usercontribs'])
        if 'continue' not in d:
            break
        cont = {'uccontinue': d['continue']['uccontinue']}
    return n


def ground_truth(username):
    info = api('meta.wikimedia.org', action='query', meta='globaluserinfo', guiuser=username,
               guiprop='merged|editcount')['query']['globaluserinfo']
    if 'missing' in info:
        return {'username': username, 'missing': True}
    merged = sorted(info.get('merged', []), key=lambda w: -w.get('editcount', 0))
    total = info.get('editcount') or sum(w.get('editcount', 0) for w in merged)
    en = next((w['editcount'] for w in merged if w['wiki'] == 'enwiki'), 0)
    babel = api('meta.wikimedia.org', action='query', meta='babel', babuser=username).get('query', {}).get('babel', {})
    return {
        'username': username,
        'globalEdits': total,
        'topWikis': [(w['wiki'], w.get('editcount', 0)) for w in merged[:6]],
        'enwikiEdits': en,
        'enwikiShare': round(en / total, 4) if total else 0,
        'homeWiki': merged[0]['wiki'] if merged else None,
        'babel': babel,
        'enwikiCreations': creations(username) if en else 0,
    }


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('users', nargs='+')
    a = ap.parse_args()
    rows = [ground_truth(u) for u in a.users]
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, '_ground_truth.json'), 'w') as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)
    print('| Editor | Global edits | Top wikis | enwiki share | Babel | enwiki creations |')
    print('|---|---:|---|---:|---|---:|')
    for r in rows:
        if r.get('missing'):
            print(f"| {r['username']} | MISSING | | | | |")
            continue
        tops = ' · '.join(f'{w} {c:,}' for w, c in r['topWikis'][:4])
        print(f"| {r['username']} | {r['globalEdits']:,} | {tops} | {r['enwikiShare']:.1%} | {r['babel'] or '—'} | {r['enwikiCreations']} |")
