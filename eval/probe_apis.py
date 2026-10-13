"""Re-verify every Wikimedia API that WIKIMEDIA-RESEARCH.md relies on. Read-only.

Usage:
  python eval/probe_apis.py

Prints PASS/FAIL per check with a short detail. A FAIL means the research doc
(and any Compass code built on that API) needs revisiting.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import api, session  # noqa: E402

EN, ML = 'en.wikipedia.org', 'ml.wikipedia.org'
LW = 'https://api.wikimedia.org/service/lw'


def hits(q, host=EN):
    return api(host, action='query', list='search', srsearch=q, srlimit=1)['query']['searchinfo']['totalhits']


def page(host, **p):
    return next(iter(api(host, action='query', formatversion=2, **p)['query']['pages']))


CHECKS = {
    'globaluserinfo': lambda: len(api('meta.wikimedia.org', action='query', meta='globaluserinfo', guiuser='Ranjithsiji', guiprop='merged')['query']['globaluserinfo']['merged']) > 5,
    'babel (wikidata)': lambda: 'ml' in api('www.wikidata.org', action='query', meta='babel', babuser='Netha Hussain')['query']['babel'],
    'usercontribs tags': lambda: 'tags' in api(EN, action='query', list='usercontribs', ucuser='Hog Farm', uclimit=1, ucprop='tags')['query']['usercontribs'][0],
    'pageassessments': lambda: 'Medicine' in page(EN, prop='pageassessments', titles='Tuberculosis')['pageassessments'],
    'projectpages': lambda: bool(api(EN, action='query', list='projectpages', wppprojects='Medicine', wpplimit=1)['query']['projects']['Medicine']),
    'info watchers': lambda: page(EN, prop='info', inprop='watchers', titles='Kerala').get('watchers', 0) > 30,
    'cirrusdoc weighted_tags': lambda: any('articletopic' in t for t in page(EN, prop='cirrusdoc', cdincludes='weighted_tags', titles='Koomapatti')['cirrusdoc'][0]['source']['weighted_tags']),
    'cirrusdoc on mlwiki': lambda: any('articlecountry' in t for t in page(ML, prop='cirrusdoc', cdincludes='weighted_tags', titles='കേരളം')['cirrusdoc'][0]['source']['weighted_tags']),
    'querypage Lonelypages (ml)': lambda: bool(api(ML, action='query', list='querypage', qppage='Lonelypages', qplimit=1)['query']['querypage']['results']),
    'search tracking category': lambda: hits('incategory:"All articles lacking sources" articlecountry:ind') > 100,
    'search articletopic': lambda: hits('articletopic:medicine-and-health incategory:"All articles with unsourced statements"') > 100,
    'search articlecountry alpha-3': lambda: hits('articlecountry:nga') > 1000,
    'search hasrecommendation:link (ml)': lambda: hits('hasrecommendation:link', ML) > 100,
    'search hasrecommendation:image': lambda: hits('hasrecommendation:image') > 100,
    'search nearcoord': lambda: hits('nearcoord:40km,9.97,76.28') > 50,
    'search morelikethis+filter': lambda: hits('morelikethis:"Lake Louise criteria" hastemplate:"More citations needed"') > 10,
    'rest.php page html': lambda: 'data-mw' in session.get(f'https://{EN}/w/rest.php/v1/page/Koomapatti/html', timeout=60).text,
    'rest.php history counts': lambda: session.get(f'https://{EN}/w/rest.php/v1/page/Koomapatti/history/counts/edits', timeout=60).json()['count'] > 0,
    'pageviews per-article': lambda: bool(session.get('https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/Kerala/daily/20260901/20260930', timeout=60).json().get('items')),
    'pageviews top-per-country': lambda: bool(session.get('https://wikimedia.org/api/rest_v1/metrics/pageviews/top-per-country/IN/all-access/2026/10/01', timeout=60).json().get('items')),
    'citoid DOI': lambda: session.get(f'https://{EN}/api/rest_v1/data/citation/mediawiki/10.1056%2FNEJMoa2034577', timeout=60).json()[0]['itemType'] == 'journalArticle',
    'liftwing articlequality': lambda: 'scores' in session.post(f'{LW}/inference/v1/models/enwiki-articlequality:predict', json={'rev_id': 1376786710}, timeout=60).json()['enwiki'],
    'liftwing outlink-topic (ml)': lambda: bool(session.post(f'{LW}/inference/v1/models/outlink-topic-model:predict', json={'page_title': 'കേരളം', 'lang': 'ml'}, timeout=60).json()['prediction']['results']),
    'liftwing article-country': lambda: session.post(f'{LW}/inference/v1/models/article-country:predict', json={'lang': 'en', 'title': 'Koomapatti'}, timeout=60).json()['prediction']['results'][0]['country'] == 'India',
    'liftwing revertrisk': lambda: 'probabilities' in session.post(f'{LW}/inference/v1/models/revertrisk-language-agnostic:predict', json={'rev_id': 1376786710, 'lang': 'en'}, timeout=60).json()['output'],
    'CX recommendations': lambda: bool(session.get(f'{LW}/recommendation/api/v1/translation', params={'source': 'en', 'target': 'ml', 'seed': 'Kerala', 'count': 2}, timeout=90).json()['recommendations']),
    'CX section recommendations': lambda: 'missing' in session.get(f'{LW}/recommendation/api/v1/translation/sections', params={'source': 'en', 'target': 'ml', 'seed': 'Kerala', 'count': 1}, timeout=90).json()['recommendations'][0],
    'wikibase REST labels': lambda: session.get('https://www.wikidata.org/w/rest.php/wikibase/v1/entities/items/Q1186/labels', timeout=60).json()['ml'] == 'കേരളം',
    'WDQS sparql': lambda: bool(session.get('https://query.wikidata.org/sparql', params={'query': 'SELECT ?i WHERE { ?i wdt:P131 wd:Q1800 } LIMIT 1', 'format': 'json'}, timeout=90).json()['results']['bindings']),
    'commons globalusage': lambda: 'globalusage' in page('commons.wikimedia.org', prop='globalusage', titles='File:Kaloor.jpg'),
    'xtools pages_count': lambda: session.get('https://xtools.wmcloud.org/api/user/pages_count/en.wikipedia.org/Netha_Hussain', timeout=90).json()['counts']['0']['count'] > 0,
    'cxserver section mapping': lambda: 'missing' in session.get('https://cxserver.wikimedia.org/v2/suggest/sections/Nedumudi_Venu/en/ml', timeout=60).json()['sections'],
    'commons allimages by user': lambda: bool(api('commons.wikimedia.org', action='query', list='allimages', aiuser='Ranjithsiji', aisort='timestamp', ailimit=1)['query']['allimages']),
    'openalex works search': lambda: bool(session.get('https://api.openalex.org/works', params={'search': 'Lake Louise criteria', 'per-page': 1}, timeout=60).json()['results']),
    'pubmed esearch': lambda: bool(session.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi', params={'db': 'pubmed', 'term': 'tuberculosis', 'retmode': 'json', 'retmax': 1}, timeout=60).json()['esearchresult']['idlist']),
    'campaignevents discovery': lambda: session.get(f'https://{EN}/w/rest.php/campaignevents/v0/event_discovery/discoverable_events', params={'page': 'Kerala'}, timeout=60).status_code == 200,
}

if __name__ == '__main__':
    fails = 0
    for name, fn in CHECKS.items():
        try:
            ok = bool(fn())
            detail = ''
        except Exception as e:  # report and continue
            ok, detail = False, f'{type(e).__name__}: {str(e)[:100]}'
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)
    print(f'\n{len(CHECKS) - fails}/{len(CHECKS)} passed')
    sys.exit(1 if fails else 0)
