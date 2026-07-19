import time

from services.http_client import session

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

MEGA_CATEGORY_THRESHOLD = 3000
TOP_CATEGORIES = 15
MEMBERS_PER_CATEGORY = 30


def _wiki_get(params, retries=3, api_url=WIKI_API):
    params = {**params, "format": "json"}
    for attempt in range(retries):
        r = session.get(api_url, params=params, timeout=15)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 2)) * (attempt + 1)
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("MediaWiki API rate-limited us after retries")


def _fetch_qids(prefixed_titles):
    """Resolves page titles to their Wikidata QID via pageprops.wikibase_item.

    Batches of 50 (API hard cap for `titles`). Pages with no linked
    Wikidata item are omitted from the result. Keys are stripped of any
    `Category:` prefix.
    """
    qid_map = {}
    for i in range(0, len(prefixed_titles), 50):
        batch = prefixed_titles[i:i + 50]
        if not batch:
            continue
        data = _wiki_get({
            "action": "query",
            "titles": "|".join(batch),
            "prop": "pageprops",
            "ppprop": "wikibase_item",
        })
        pages = (data.get("query") or {}).get("pages") or {}
        for pg in pages.values():
            title = pg.get("title")
            qid = (pg.get("pageprops") or {}).get("wikibase_item")
            if not title or not qid:
                continue
            qid_map[title.replace("Category:", "")] = qid
        time.sleep(0.25)
    return qid_map


def fetch_category_qids(category_titles):
    prefixed = [f"Category:{t}" if not t.startswith("Category:") else t for t in category_titles]
    return _fetch_qids(prefixed)


def fetch_article_qids(article_titles):
    return _fetch_qids(list(article_titles))


def fetch_category_info(category_titles):
    """Batched action=query&prop=categoryinfo -- returns {category_title: page_count}.

    `pages` (not `size`) is the article count -- excludes subcats/files.
    Used to skip mega-categories (e.g. "Living people") before expanding
    them into member articles, since their members aren't a meaningful
    topical signal.
    """
    info_map = {}
    prefixed = [f"Category:{t}" if not t.startswith("Category:") else t for t in category_titles]
    for i in range(0, len(prefixed), 50):
        batch = prefixed[i:i + 50]
        if not batch:
            continue
        data = _wiki_get({
            "action": "query",
            "titles": "|".join(batch),
            "prop": "categoryinfo",
        })
        pages = (data.get("query") or {}).get("pages") or {}
        for pg in pages.values():
            title = pg.get("title")
            ci = pg.get("categoryinfo")
            if not title or not ci:
                continue
            info_map[title.replace("Category:", "")] = ci.get("pages", 0)
        time.sleep(0.25)
    return info_map


def fetch_category_members(category_title, limit=MEMBERS_PER_CATEGORY):
    """Up to `limit` namespace-0 (article) members of a category. Single
    page, no deep pagination -- this is a sampling step, not a full crawl.
    """
    title = category_title if category_title.startswith("Category:") else f"Category:{category_title}"
    data = _wiki_get({
        "action": "query",
        "list": "categorymembers",
        "cmtitle": title,
        "cmnamespace": 0,
        "cmlimit": limit,
    })
    members = (data.get("query") or {}).get("categorymembers") or []
    return [m["title"] for m in members if m.get("title")]


def fetch_sitelinks(qids):
    """Batched wbgetentities -- returns {qid: set(dbname)} of wikis that
    already have a page for that Wikidata item.
    """
    sitelinks_map = {}
    qid_list = list(qids)
    for i in range(0, len(qid_list), 50):
        batch = qid_list[i:i + 50]
        if not batch:
            continue
        data = _wiki_get({
            "action": "wbgetentities",
            "ids": "|".join(batch),
            "props": "sitelinks",
        }, api_url=WIKIDATA_API)
        entities = data.get("entities") or {}
        for qid, entity in entities.items():
            sitelinks = entity.get("sitelinks") or {}
            sitelinks_map[qid] = set(sitelinks.keys())
        time.sleep(0.25)
    return sitelinks_map
