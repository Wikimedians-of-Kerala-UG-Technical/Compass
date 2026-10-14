"""Replay the frontend's load sequence for one or more users and save every response.

Mirrors frontend/src/stores/appStore.js start():
  profile -> trends (profile country + home wiki) -> revisit -> tasks
  -> geo -> tasks again near geo.focus.local -> discover (focus region/local)
  -> contribute (focus local or region)

Usage:
  python eval/harness.py --out eval/runs/2026-10-13 "Ranjithsiji" "Netha Hussain"

Writes <out>/<user>/{profile,trends,revisit,tasks1,geo,tasks2,discover,contribute}.json
and _timing.json. If the frontend's call sequence changes, update this file to match it
before running. Version 1 of this harness (for the pre-October-2026 API) is in git history.
"""
import argparse
import json
import os
import sys
import time
from urllib.parse import quote

import requests

sys.path.insert(0, os.path.dirname(__file__))
from common import BACKEND, safe_dirname  # noqa: E402


def run_user(username, out_root):
    out = os.path.join(out_root, safe_dirname(username))
    os.makedirs(out, exist_ok=True)
    timing = {}

    def call(name, path, params=None):
        t0 = time.time()
        try:
            r = requests.get(BACKEND + path, params=params, timeout=900)
            status, body = r.status_code, r.json()
        except Exception as e:  # record the failure, keep going
            status, body = -1, {'error': repr(e)}
        timing[name] = {'status': status, 'secs': round(time.time() - t0, 1)}
        with open(os.path.join(out, f'{name}.json'), 'w') as f:
            json.dump(body, f, indent=1, ensure_ascii=False)
        print(f'{username:24} {name:9} {status} {timing[name]["secs"]}s', flush=True)
        return body

    u = quote(username)
    profile = call('profile', f'/api/profile/{u}')
    if 'error' not in profile:
        country = (profile.get('countries') or [{}])[0].get('a2')
        langs = ','.join(l['lang'] for l in profile.get('languages') or [] if l['lang'] != profile.get('homeLang'))
        call('trends', '/api/trends', {'country': country, 'wiki': profile['homeWiki'], 'langs': langs})
        call('revisit', f'/api/revisit/{u}')
        call('tasks1', f'/api/tasks/{u}')
        geo = call('geo', f'/api/geo/{u}')
        focus = (geo.get('focus') or {}) if 'error' not in geo else {}
        local, region = focus.get('local'), focus.get('region')
        timing['geoFocus'] = {'local': (local or {}).get('nameEn') or (local or {}).get('name'),
                              'region': (region or {}).get('nameEn') or (region or {}).get('name')}
        if local and local.get('coord'):
            call('tasks2', f'/api/tasks/{u}', {'lat': local['coord']['lat'], 'lon': local['coord']['lon'],
                                               'place': local['name']})
        call('discover', f'/api/discover/{u}', {'region': (region or {}).get('qid'), 'local': (local or {}).get('qid'),
                                                'regionName': (region or {}).get('name')})
        place = local or region or {}
        call('contribute', f'/api/contribute/{u}', {'place': place.get('qid'), 'placeName': place.get('name')})

    with open(os.path.join(out, '_timing.json'), 'w') as f:
        json.dump(timing, f, indent=1)


def run_trends(out_root):
    t0 = time.time()
    r = requests.get(BACKEND + '/api/trends', timeout=300)
    os.makedirs(out_root, exist_ok=True)
    with open(os.path.join(out_root, '_trends.json'), 'w') as f:
        json.dump({'status': r.status_code, 'secs': round(time.time() - t0, 1), 'body': r.json()}, f, indent=1, ensure_ascii=False)
    print(f'trends {r.status_code} {round(time.time() - t0, 1)}s')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--trends', action='store_true', help='also capture /api/trends once')
    ap.add_argument('users', nargs='*')
    a = ap.parse_args()
    if a.trends:
        run_trends(a.out)
    for user in a.users:
        run_user(user, a.out)
