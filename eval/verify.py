"""Spot-check claims Compass makes, against live Wikimedia data.

Subcommands (all read-only):
  pageviews TITLE...            real avg daily pageviews (last 30 days, user agent) — compare with a task's `pageviews`
  tags TITLE...                 maintenance tracking categories (incl. hidden) — compare with Revisit tags
  shape TITLE...                size, <ref> count, {{citation needed}} count, refimprove/unreferenced tag present
  sitelinks --wiki mlwiki TITLE...   does the enwiki article's Wikidata item have a page on --wiki? — check Discover
  search [--wiki en] QUERY...   CirrusSearch hit count + top titles — compare current vs alternative task queries
  newcomers                     list enwiki accounts with 40–400 edits making Growth `newcomer task` edits right now

Examples:
  python eval/verify.py pageviews "Kerala"
  python eval/verify.py search 'hastemplate:"Citation needed" medicine' 'hastemplate:"Citation needed" articletopic:medicine-and-health'
"""
import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
from common import api, session  # noqa: E402

EN = 'en.wikipedia.org'
MAINT_KW = ['unsourced', 'references', 'sources', 'orphan', 'cleanup', 'updat', 'disputed', 'npov', 'stub']


def pageviews(titles):
    end = datetime.now(timezone.utc) - timedelta(days=1)
    start = end - timedelta(days=30)
    for t in titles:
        url = ('https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/'
               f'{t.replace(" ", "_")}/daily/{start:%Y%m%d}/{end:%Y%m%d}')
        items = session.get(url).json().get('items', [])
        avg = sum(i['views'] for i in items) // max(len(items), 1)
        print(f'{t}: avg {avg}/day over {len(items)} days')


def tags(titles):
    for t in titles:
        d = api(EN, action='query', titles=t, prop='categories|info', cllimit='max')
        pg = next(iter(d['query']['pages'].values()))
        cats = [c['title'][9:] for c in pg.get('categories', []) if any(k in c['title'].lower() for k in MAINT_KW)]
        print(f'{t} (length {pg.get("length")}):')
        for c in cats:
            print('   ', c)


def shape(titles):
    for t in titles:
        wt = api(EN, action='parse', page=t, prop='wikitext', redirects=1)['parse']['wikitext']['*']
        cn = len(re.findall(r'\{\{\s*(cn|citation needed|fact)\b', wt, re.I))
        tag = bool(re.search(r'\{\{\s*(unreferenced|more citations needed|refimprove)', wt, re.I))
        print(f'{t}: {len(wt):,} bytes, {wt.count("<ref")} <ref>, {cn} citation-needed, refs-tag={tag}')


def sitelinks(titles, wiki):
    for t in titles:
        pp = api(EN, action='query', titles=t, prop='pageprops', ppprop='wikibase_item')
        qid = (next(iter(pp['query']['pages'].values())).get('pageprops') or {}).get('wikibase_item')
        if not qid:
            print(f'{t}: no Wikidata item')
            continue
        sl = api('www.wikidata.org', action='wbgetentities', ids=qid, props='sitelinks')['entities'][qid]['sitelinks']
        print(f'{t} ({qid}): {"PRESENT" if wiki in sl else "MISSING"} on {wiki}; {len(sl)} sitelinks')


def search(queries, wiki):
    for q in queries:
        d = api(f'{wiki}.wikipedia.org', action='query', list='search', srsearch=q, srlimit=6, srnamespace=0)
        if 'error' in d:
            print(f'ERROR {q}: {d["error"]["info"]}')
            continue
        hits = d['query']['searchinfo']['totalhits']
        print(f'hits={hits:<7} {q}\n           {[r["title"] for r in d["query"]["search"]]}')


def newcomers():
    rc = api(EN, action='query', list='recentchanges', rctag='newcomer task', rclimit=200, rcprop='user', rctype='edit')
    users = list(dict.fromkeys(r['user'] for r in rc['query']['recentchanges']))[:50]
    info = api(EN, action='query', list='users', ususers='|'.join(users), usprop='editcount|registration')
    for u in info['query']['users']:
        if 40 <= u.get('editcount', 0) <= 400:
            print(u['name'], u['editcount'], u.get('registration'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ['pageviews', 'tags', 'shape']:
        sub.add_parser(name).add_argument('titles', nargs='+')
    p = sub.add_parser('sitelinks')
    p.add_argument('--wiki', required=True)
    p.add_argument('titles', nargs='+')
    p = sub.add_parser('search')
    p.add_argument('--wiki', default='en')
    p.add_argument('queries', nargs='+')
    sub.add_parser('newcomers')
    a = ap.parse_args()
    if a.cmd == 'pageviews':
        pageviews(a.titles)
    elif a.cmd == 'tags':
        tags(a.titles)
    elif a.cmd == 'shape':
        shape(a.titles)
    elif a.cmd == 'sitelinks':
        sitelinks(a.titles, a.wiki)
    elif a.cmd == 'search':
        search(a.queries, a.wiki)
    elif a.cmd == 'newcomers':
        newcomers()
