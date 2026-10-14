"""Article Guide: what exactly needs work in one article, on any Wikipedia.

Reads Parsoid HTML (`rest.php/v1/page/{title}/html`), where every section is a
<section> and every template carries its parameters in `data-mw`. That lets the guide
point at the exact uncited paragraph, list each inline tag with its date, find dead
links and bare URLs, and compare the article with its Wikidata item (image, birth date…)
and with the same article in other languages (missing sections, via Content Translation).
"""
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup

from services import wiki
from services.signals import article_signals, dated_tags
from services.discover_service import cx_url

_cache = wiki.TTLCache(ttl=3600, maxsize=500, name='guide')
CXSERVER = 'https://cxserver.wikimedia.org/v2/suggest/sections'

# English names of inline problem templates (lowercase, first letter-insensitive).
INLINE_TAGS = {
    'citation needed': 'Citation needed', 'cn': 'Citation needed', 'fact': 'Citation needed',
    'dead link': 'Dead link', 'failed verification': 'Failed verification',
    'better source needed': 'Better source needed', 'better source': 'Better source needed',
    'clarify': 'Clarify', 'who?': 'Who?', 'when?': 'When?', 'which?': 'Which?', 'by whom?': 'By whom?',
    'page needed': 'Page number needed', 'update inline': 'Needs update', 'according to whom?': 'According to whom?',
    'unreliable source?': 'Unreliable source?', 'self-published inline': 'Self-published source',
    'vague': 'Vague', 'dubious': 'Dubious', 'year needed': 'Year needed',
}
SKIP_SECTIONS = re.compile(r'^(references|notes|citations|footnotes|sources|bibliography|external links|see also|further reading|works|filmography|discography|gallery)$', re.I)
QUALITY_NEXT = {
    'Stub': 'Start-class needs a few paragraphs of sourced prose covering the main points.',
    'Start': 'C-class needs most sections written and the major claims cited.',
    'C': 'B-class needs every claim cited, broad coverage, a lead that summarises, and an image or infobox where relevant.',
    'B': 'Good Article: a full review (WP:GACR): well-written, broad, neutral, stable, illustrated, verifiable.',
}
LEAD_MIN_CHARS = 250


def _template_name(target_wt):
    name = (target_wt or '').strip().split('|')[0].replace('_', ' ')
    name = name.split(':', 1)[1] if name.lower().startswith('template:') else name
    return name.strip()


def _local_inline_names(dbname):
    """Local names of the inline templates on this wiki (Template:Citation needed -> ഫലകം:തെളിവ്)."""
    if dbname == 'enwiki':
        return {}
    from services.maintenance import _local_names
    try:
        mapped = _local_names(dbname, 'Template', sorted({v for v in INLINE_TAGS.values()}))
    except Exception:
        return {}
    return {local.lower(): english for english, local in mapped.items()}


def _parse_html(html, dbname):
    soup = BeautifulSoup(html, 'html.parser')
    local_inline = _local_inline_names(dbname)
    sections, inline, templates, bare_urls, dead_links = [], [], [], 0, 0
    cited_urls = set()
    infobox = bool(soup.select_one('table.infobox, .infobox'))
    images = len(soup.select('figure, [typeof~="mw:File"], [typeof~="mw:File/Thumb"], [typeof~="mw:File/Frame"]'))

    for el in soup.select('[typeof~="mw:Transclusion"]'):
        try:
            dm = json.loads(el.get('data-mw') or '{}')
        except ValueError:
            continue
        for part in dm.get('parts') or []:
            if not isinstance(part, dict) or 'template' not in part:
                continue
            t = part['template']
            name = _template_name((t.get('target') or {}).get('wt'))
            params = {k: (v or {}).get('wt', '') for k, v in (t.get('params') or {}).items()}
            templates.append((name, params, el))
            key = name.lower()
            english = INLINE_TAGS.get(key) or local_inline.get(key)
            if english:
                inline.append({'tag': english, 'template': name, 'date': params.get('date') or None, 'el': el})
            if english == 'Dead link':
                dead_links += 1
            url = params.get('url')
            if url:
                cited_urls.add(url.strip())
                if params.get('url-status') == 'dead' and not params.get('archive-url'):
                    dead_links += 1

    for a in soup.select('ol.mw-references a.external, ol.references a.external'):
        href = a.get('href', '')
        # A citation that is only a URL renders as a "free" external link.
        if 'free' in (a.get('class') or []) and not a.find_parent('cite'):
            bare_urls += 1
        cited_urls.add(href)

    def section_of(el):
        sec = el.find_parent('section')
        return sec.get('data-mw-section-id') if sec else None

    for sec in soup.find_all('section'):
        heading = sec.find(['h2', 'h3', 'h4', 'h5', 'h6'], recursive=False)
        name = heading.get_text(' ', strip=True) if heading else '(Lead)'
        level = int(heading.name[1]) if heading else 1
        sid = sec.get('data-mw-section-id')
        paras = [p for p in sec.find_all('p', recursive=False) if len(p.get_text(strip=True)) > 0]
        text_len = sum(len(p.get_text(' ', strip=True)) for p in paras)
        refs = sum(len(p.select('sup.mw-ref, [typeof~="mw:Extension/ref"]')) for p in paras)
        uncited = []
        if not SKIP_SECTIONS.match(name):
            for p in paras:
                text = p.get_text(' ', strip=True)
                if len(text) >= 150 and not p.select('sup.mw-ref, [typeof~="mw:Extension/ref"]'):
                    uncited.append(re.sub(r'\s+', ' ', text)[:140])
        sections.append({
            'id': sid, 'name': name, 'level': level, 'chars': text_len, 'refCount': refs,
            'uncitedParagraphs': uncited,
            'inlineTags': [],
        })

    by_id = {s['id']: s for s in sections}
    for tag in inline:
        sec = by_id.get(section_of(tag['el']))
        sentence = ''
        parent = tag['el'].find_parent(['p', 'li', 'td'])
        if parent:
            sentence = re.sub(r'\s+', ' ', parent.get_text(' ', strip=True))[:140]
        item = {'tag': tag['tag'], 'template': tag['template'], 'date': tag['date'], 'context': sentence}
        if sec is not None:
            sec['inlineTags'].append(item)

    lead = by_id.get('0') or (sections[0] if sections else None)
    return {
        'sections': sections,
        'templates': [(n, p) for n, p, _ in templates],
        'inline': [{k: v for k, v in t.items() if k != 'el'} for t in inline],
        'infobox': infobox,
        'images': images,
        'bareUrls': bare_urls,
        'deadLinks': dead_links,
        'citedUrls': sorted(u for u in cited_urls if u),
        'leadChars': lead['chars'] if lead else 0,
    }


def _wikidata(dbname, title):
    """Wikidata item for the article: image (P18), Commons category (P373), birth/death
    dates, and which languages already have an article."""
    data = wiki.api(dbname, {'action': 'query', 'titles': title, 'prop': 'pageprops', 'ppprop': 'wikibase_item', 'redirects': 1})
    pages = (data.get('query') or {}).get('pages') or []
    qid = ((pages[0].get('pageprops') or {}).get('wikibase_item')) if pages else None
    if not qid:
        return None
    ent = (wiki.api('wikidatawiki', {'action': 'wbgetentities', 'ids': qid, 'props': 'claims|sitelinks'})
           .get('entities') or {}).get(qid) or {}
    claims = ent.get('claims') or {}

    def first(prop):
        for s in claims.get(prop, []):
            if s.get('rank') == 'deprecated':
                continue
            try:
                return s['mainsnak']['datavalue']['value']
            except (KeyError, TypeError):
                continue
        return None

    image = first('P18')
    born = first('P569')
    died = first('P570')
    return {
        'qid': qid,
        'url': f'https://www.wikidata.org/wiki/{qid}',
        'image': image,
        'imageUrl': f'https://commons.wikimedia.org/wiki/Special:FilePath/{wiki.quote_title(image)}?width=320' if image else None,
        'commonsCategory': first('P373'),
        'born': born['time'][1:11] if isinstance(born, dict) and born.get('time') else None,
        'died': died['time'][1:11] if isinstance(died, dict) and died.get('time') else None,
        'sitelinks': sorted((ent.get('sitelinks') or {}).keys()),
    }


def _missing_sections(dbname, title, sitelinks):
    """Sections the English article has that this one lacks, with the heading already
    translated, from Content Translation's section-mapping service (cxserver)."""
    lang = wiki.lang(dbname)
    if lang == 'en' or 'enwiki' not in (sitelinks or []):
        return []
    en_title = None
    for page in wiki.api_pages(dbname, [title], {'action': 'query', 'prop': 'langlinks', 'lllang': 'en'}):
        links = page.get('langlinks') or []
        en_title = links[0]['title'] if links else None
    if not en_title:
        return []
    data = wiki.get_json(f'{CXSERVER}/{wiki.quote_title(en_title).replace("/", "%2F")}/en/{lang}', retries=1, timeout=30)
    mapping = (data or {}).get('sections') or {}
    return [{'section': sec, 'targetHeading': heading,
             'translateUrl': cx_url(dbname, en_title, 'en', lang, sec)}
            for sec, heading in (mapping.get('missing') or {}).items()
            if sec not in ('References', 'External links', 'See also', 'Notes', 'Further reading', 'Sources', 'Bibliography')]


def analyze_article(title, dbname='enwiki'):
    if os.environ.get('STRESS_TEST') == '1':
        # Canned response for locustfile.py, so load tests never hit Wikimedia.
        time.sleep(0.1)
        return {'title': title, 'wiki': dbname, 'sections': [], 'suggestions': [], 'missingSections': [],
                'inlineTags': [], 'citedUrls': [], 'topics': [], 'totalRefs': 0, 'currentSize': 0,
                'hasInfobox': False, 'hasImages': False, 'wikidata': None, 'quality': None}
    key = (dbname, title)
    cached = _cache.get(key)
    if cached:
        return cached
    t0 = time.time()
    try:
        html = wiki.get_text(f'https://{wiki.host(dbname)}/w/rest.php/v1/page/{wiki.quote_title(title).replace("/", "%2F")}/html')
    except Exception as e:
        return {'error': f'Could not load “{title}” from {dbname}: {e}', 'title': title}

    with ThreadPoolExecutor(max_workers=3) as pool:
        sig_f = pool.submit(article_signals, dbname, [title])
        wd_f = pool.submit(_wikidata, dbname, title)
        parsed = _parse_html(html, dbname)
        sig = sig_f.result().get(title) or {}
        try:
            wd = wd_f.result()
        except Exception:
            wd = None
    try:
        missing = _missing_sections(dbname, title, (wd or {}).get('sitelinks'))
    except Exception:
        missing = []

    suggestions = []
    for sec in parsed['sections']:
        for p in sec['uncitedParagraphs']:
            suggestions.append({'type': 'refs', 'section': sec['name'],
                                'text': f'Cite the paragraph in “{sec["name"]}” starting “{p[:90]}…”'})
        for tag in sec['inlineTags']:
            when = f' (since {tag["date"]})' if tag['date'] else ''
            where = 'a citation' if SKIP_SECTIONS.match(sec['name']) else f'“{sec["name"]}”'
            suggestions.append({'type': 'inline', 'section': sec['name'],
                                'text': f'{tag["tag"]}{when} in {where}: “{tag["context"][:100]}…”'})
    tags = dated_tags(sig.get('categories') or [])
    for issue, since in sorted(tags.items(), key=lambda kv: kv[1]):
        if issue.startswith(('Use ', 'Articles with short description', 'Pages ', 'Wikipedia articles written')):
            continue
        suggestions.append({'type': 'banner', 'text': f'{issue} (tagged {since})'})
    if parsed['deadLinks']:
        suggestions.append({'type': 'links', 'text': f'{parsed["deadLinks"]} dead link(s) — replace or add an archive URL'})
    if parsed['bareUrls']:
        suggestions.append({'type': 'refs', 'text': f'{parsed["bareUrls"]} bare URL reference(s) — expand into full citations'})
    if parsed['leadChars'] < LEAD_MIN_CHARS and sum(s['chars'] for s in parsed['sections']) > 3000:
        suggestions.append({'type': 'structure', 'text': f'Lead is only {parsed["leadChars"]} characters — summarise the article in it'})
    if not parsed['images'] and wd and wd.get('image'):
        suggestions.append({'type': 'media', 'text': f'Add the Wikidata image “{wd["image"]}”', 'image': wd['imageUrl']})
    elif not parsed['images'] and wd and wd.get('commonsCategory'):
        suggestions.append({'type': 'media', 'text': f'Pick an image from Commons category “{wd["commonsCategory"]}”',
                            'url': f'https://commons.wikimedia.org/wiki/Category:{wiki.quote_title(wd["commonsCategory"])}'})
    if 'image' in (sig.get('recommendations') or []) and not parsed['images']:
        suggestions.append({'type': 'media', 'text': 'Wikipedia has a suggested image for this article (Add an image task)'})
    for m in missing[:6]:
        suggestions.append({'type': 'section', 'text': f'Add “{m["targetHeading"]}” ({m["section"]}) — exists in the English article',
                            'url': m['translateUrl']})
    if wd and wd.get('born') and not re.search(wd['born'][:4], html[:20000]):
        suggestions.append({'type': 'facts', 'text': f'Wikidata has a birth date ({wd["born"]}) that the article may be missing'})

    quality = sig.get('quality')
    total_refs = sum(s['refCount'] for s in parsed['sections'])
    res = {
        'title': title,
        'wiki': dbname,
        'url': wiki.page_url(dbname, title),
        'editUrl': wiki.edit_url(dbname, title),
        'quality': quality,
        'qualityNext': QUALITY_NEXT.get(quality),
        'importance': sig.get('importance'),
        'wikiprojects': sig.get('wikiprojects') or [],
        'topics': [k.split('.')[-1].rstrip('*').replace('_', ' ') for k, w in
                   sorted((sig.get('topics') or {}).items(), key=lambda kv: -kv[1])][:4],
        'currentSize': sig.get('bytes') or len(html),
        'totalRefs': total_refs,
        'hasInfobox': parsed['infobox'],
        'hasImages': parsed['images'] > 0,
        'sections': [{k: v for k, v in s.items()} for s in parsed['sections']],
        'inlineTags': parsed['inline'],
        'missingSections': missing,
        'wikidata': wd,
        'citedUrls': parsed['citedUrls'],
        'suggestions': suggestions,
        'secs': round(time.time() - t0, 1),
    }
    _cache.set(key, res)
    return res
