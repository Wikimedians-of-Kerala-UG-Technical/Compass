"""Exercise the Article Guide endpoints for a list of article titles.

Usage:
  python eval/articles.py --out eval/runs/2026-10-13 "Tuberculosis" "Koomapatti"
  python eval/articles.py --out eval/runs/2026-10-13 --wiki mlwiki "നെടുമുടി വേണു"

Writes <out>/_articles/<title>.json with guide / external-references responses, their
HTTP status and latency, and prints a short digest. (The v1 API also had /references;
it was removed, so v1 runs used an older version of this script — see git history.)
"""
import argparse
import json
import os
import sys
import time
from urllib.parse import quote

import requests

sys.path.insert(0, os.path.dirname(__file__))
from common import BACKEND  # noqa: E402

ENDPOINTS = ['guide', 'external-references']


def run(title, out_dir, wiki=None):
    res = {}
    for ep in ENDPOINTS:
        t0 = time.time()
        r = requests.get(f'{BACKEND}/api/article/{quote(title, safe="")}/{ep}', params={'wiki': wiki} if wiki else None, timeout=300)
        try:
            body = r.json()
        except ValueError:
            body = {'error': f'non-JSON response ({r.status_code})'}
        res[ep] = {'status': r.status_code, 'secs': round(time.time() - t0, 1), 'body': body}
    with open(os.path.join(out_dir, title.replace('/', '_') + '.json'), 'w') as f:
        json.dump(res, f, indent=1, ensure_ascii=False)

    g = res['guide']['body']
    print(f"\n=== {title}  " + ' | '.join(f"{ep} {res[ep]['status']} {res[ep]['secs']}s" for ep in ENDPOINTS))
    print('  quality', g.get('quality'), 'size', g.get('currentSize'), 'refs', g.get('totalRefs'),
          'missing sections', [m['section'] for m in g.get('missingSections', [])])
    print('  suggestions:', [s['text'][:120] for s in g.get('suggestions', [])][:10])
    ext = res['external-references']['body'].get('results', [])
    print('  external sources:', sorted({x['source'] for x in ext}), f'({len(ext)} results,',
          sum(1 for x in ext if x.get('cite')), 'with a citation template)')
    for x in ext[:8]:
        print('    -', x['source'][:16], '|', (x.get('title') or '')[:90])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--wiki', help='dbname, e.g. mlwiki (default: the backend default, enwiki)')
    ap.add_argument('titles', nargs='+')
    a = ap.parse_args()
    out_dir = os.path.join(a.out, '_articles')
    os.makedirs(out_dir, exist_ok=True)
    for t in a.titles:
        run(t, out_dir, a.wiki)
