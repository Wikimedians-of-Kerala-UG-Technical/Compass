"""Maintenance tags ("work needed") on any Wikipedia.

On enwiki the precise index is the hidden tracking categories ("All articles lacking
sources"), not `hastemplate:`, which also matches templates nested inside others
(`{{Unreferenced section}}` contains `{{Unreferenced}}`, so *Lok Sabha* would count as
unreferenced). Other wikis name their templates and categories differently, so both are
mapped from English through interlanguage links (which come from Wikidata), e.g.
Template:Citation needed -> ml: ഫലകം:തെളിവ്.
"""
from services import wiki

# key -> English template, English tracking category, task label, minutes, effort, urgency
ISSUES = {
    'add_citations': {
        'template': 'Citation needed', 'category': 'All articles with unsourced statements',
        'label': 'Add citations', 'short': 'Citation needed', 'minutes': 10, 'effort': 'low', 'urgency': .65,
    },
    'add_refs': {
        'template': 'Unreferenced', 'category': 'All articles lacking sources',
        'label': 'Add references', 'short': 'Unreferenced', 'minutes': 20, 'effort': 'med', 'urgency': .8,
    },
    'more_refs': {
        'template': 'More citations needed', 'category': 'All articles needing additional references',
        'label': 'Add more references', 'short': 'Needs more references', 'minutes': 20, 'effort': 'med', 'urgency': .7,
    },
    'inline_cites': {
        'template': 'No footnotes', 'category': 'All articles lacking in-text citations',
        'label': 'Add inline citations', 'short': 'No inline citations', 'minutes': 25, 'effort': 'med', 'urgency': .5,
    },
    'fix_orphan': {
        'template': 'Orphan', 'category': 'All orphaned articles',
        'label': 'Link from other articles', 'short': 'Orphan', 'minutes': 10, 'effort': 'low', 'urgency': .4,
    },
    'dead_links': {
        'template': 'Dead link', 'category': 'All articles with dead external links',
        'label': 'Fix dead links', 'short': 'Dead links', 'minutes': 10, 'effort': 'low', 'urgency': .35,
    },
    'expand': {
        'template': 'Expand section', 'category': 'All articles to be expanded',
        'label': 'Expand a section', 'short': 'Needs expansion', 'minutes': 30, 'effort': 'high', 'urgency': .45,
    },
    'update': {
        'template': 'Update', 'category': 'All Wikipedia articles in need of updating',
        'label': 'Update outdated content', 'short': 'Needs update', 'minutes': 20, 'effort': 'med', 'urgency': .5,
    },
    'disputed': {
        'template': 'Disputed', 'category': 'All accuracy disputes',
        'label': 'Check disputed facts', 'short': 'Accuracy disputed', 'minutes': 30, 'effort': 'high', 'urgency': .5,
    },
    'npov': {
        'template': 'POV', 'category': 'All NPOV disputes',
        'label': 'Fix neutrality', 'short': 'Neutrality disputed', 'minutes': 30, 'effort': 'high', 'urgency': .45,
    },
    'stub': {
        'template': 'Stub', 'category': 'All stub articles',
        'label': 'Expand stub', 'short': 'Stub', 'minutes': 30, 'effort': 'med', 'urgency': .3,
    },
}

# Machine-prepared Growth tasks (CirrusSearch `hasrecommendation:`), no template needed.
RECOMMENDATIONS = {
    'add_link': {'keyword': 'link', 'label': 'Add links', 'short': 'Suggested links', 'minutes': 5, 'effort': 'low', 'urgency': .35},
    'add_image': {'keyword': 'image', 'label': 'Add an image', 'short': 'Suggested image', 'minutes': 5, 'effort': 'low', 'urgency': .4},
}

# Tasks the recommender searches for (stub/disputed/npov are only reported in Revisit).
TASK_KEYS = ['add_refs', 'add_citations', 'more_refs', 'fix_orphan', 'dead_links', 'expand']

_cache = wiki.TTLCache(ttl=7 * 24 * 3600, name='maintenance')


def _local_names(dbname, ns_prefix, names):
    """English 'Template:X'/'Category:X' -> local page title (without namespace) on dbname."""
    if dbname == 'enwiki':
        return {n: n for n in names}
    language = wiki.lang(dbname)
    out = {}
    titles = [f'{ns_prefix}:{n}' for n in names]
    for page in wiki.api_pages('enwiki', titles, {'action': 'query', 'prop': 'langlinks', 'lllang': language}):
        links = page.get('langlinks') or []
        if links:
            out[page['title'].split(':', 1)[1]] = links[0]['title'].split(':', 1)[1]
    return out


def local_issues(dbname):
    """Per-wiki issue map: key -> {template, category} local names (either may be None),
    plus category page counts so empty mappings can be skipped."""
    def compute():
        tpl = _local_names(dbname, 'Template', [i['template'] for i in ISSUES.values()])
        cat = _local_names(dbname, 'Category', [i['category'] for i in ISSUES.values()])
        counts = {}
        cat_titles = [f'Category:{c}' for c in cat.values()]
        for page in wiki.api_pages(dbname, cat_titles, {'action': 'query', 'prop': 'categoryinfo'}):
            counts[page['title'].split(':', 1)[1]] = (page.get('categoryinfo') or {}).get('pages', 0)
        out = {}
        for key, issue in ISSUES.items():
            local_cat = cat.get(issue['category'])
            out[key] = {
                'template': tpl.get(issue['template']),
                'category': local_cat if counts.get(local_cat, 0) > 0 else None,
                'categoryCount': counts.get(local_cat, 0),
            }
        return out
    return _cache.get_or_compute(('issues', dbname), compute)


def search_filter(dbname, key):
    """CirrusSearch filter that selects articles with this issue on dbname, or None."""
    if key in RECOMMENDATIONS:
        return f'hasrecommendation:{RECOMMENDATIONS[key]["keyword"]}'
    local = local_issues(dbname).get(key) or {}
    if use_category(dbname, local):
        return f'incategory:"{local["category"]}"'
    if local.get('template'):
        return f'hastemplate:"{local["template"]}"'
    return None


def use_category(dbname, local):
    """Prefer the tracking category (precise), unless the wiki barely uses it and the
    template is the better index (mlwiki's unsourced-statements category has ~500
    pages while its {{തെളിവ്}} template is on thousands)."""
    if not local.get('category'):
        return False
    return dbname == 'enwiki' or not local.get('template') or local.get('categoryCount', 0) >= 1000


def issues_of(dbname, sig):
    """Which issues an article has, from its cirrusdoc categories/templates.
    Uses tracking categories where the wiki has them, else direct templates."""
    local = local_issues(dbname)
    cats = set(sig.get('categories') or [])
    templates = set(sig.get('templates') or [])
    found = []
    for key, names in local.items():
        if names.get('category') and names['category'] in cats:
            found.append(key)
        elif dbname != 'enwiki' and names.get('template') and names['template'] in templates:
            # Other wikis often lack the tracking categories, so the template itself counts.
            found.append(key)
    if dbname == 'enwiki':
        # 'Unreferenced' trumps 'More citations needed'; don't report both.
        if 'add_refs' in found and 'more_refs' in found:
            found.remove('more_refs')
    for key, rec in RECOMMENDATIONS.items():
        if rec['keyword'] in (sig.get('recommendations') or []):
            found.append(key)
    return found


def meta(key):
    return ISSUES.get(key) or RECOMMENDATIONS.get(key) or {
        'label': key, 'short': key, 'minutes': 20, 'effort': 'med', 'urgency': .5}
