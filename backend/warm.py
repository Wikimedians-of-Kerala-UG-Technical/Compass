"""Pre-warms the caches for editors who visit often, so their dashboard opens fast.

    python warm.py Ranjithsiji "Netha Hussain" Rosiestep
    python warm.py --file regulars.txt      # one username per line

Run it from cron a little more often than the profile cache expires (6 h). It builds
the same profile, geo, tasks, revisit and discover results the dashboard asks for.
"""
import argparse
import sys
import time

from services import wiki
from services.discover_service import find_discover
from services.geo_service import resolve_geo
from services.profile_service import build_profile
from services.revisit_service import find_revisit
from services.task_service import find_tasks


def warm(username):
    t0 = time.time()
    profile = build_profile(username)
    geo = resolve_geo(profile['homeWiki'], profile['_editedTitles'])
    local = (geo.get('focus') or {}).get('local')
    region = (geo.get('focus') or {}).get('region')
    find_tasks(profile, local if local and local.get('coord') else None)
    find_revisit(profile)
    if region or local:
        find_discover(profile, {'qid': (region or {}).get('qid'), 'localQid': (local or {}).get('qid'),
                                'name': (region or {}).get('name')})
    else:
        find_discover(profile)
    return time.time() - t0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('usernames', nargs='*')
    parser.add_argument('--file', help='file with one username per line')
    args = parser.parse_args(argv)
    names = list(args.usernames)
    if args.file:
        with open(args.file, encoding='utf-8') as f:
            names += [line.strip() for line in f if line.strip() and not line.startswith('#')]
    if not names:
        parser.error('give at least one username')
    failed = 0
    for name in names:
        try:
            print(f'{wiki.normalize_username(name)}: {warm(name):.1f} s')
        except Exception as e:
            failed += 1
            print(f'{name}: failed ({e})', file=sys.stderr)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
