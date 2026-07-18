import time
import re
from services.http_client import session

WIKI_API = "https://en.wikipedia.org/w/api.php"

TOPIC_KW = {
    "medicine": ["medic", "disease", "health", "hospital", "drug", "pharma", "anatomy", "surg",
                 "radiol", "pathol", "diagnos", "therap", "clinic", "symptom", "syndrome",
                 "cancer", "infect", "epidem", "virus", "bacter"],
    "science": ["science", "physic", "chemi", "biolog", "math", "astrono", "geolog", "ecolog", "genetic"],
    "technology": ["technol", "comput", "software", "internet", "digital", "program", "engineer", "robot"],
    "geography": ["geograph", "countr", "city", "cities", "district", "village", "town", "region", "province"],
    "history": ["histor", "ancient", "mediev", "century", "war ", "empire", "dynasty", "colonial"],
    "culture": ["cultur", "music", "film", "art ", "literat", "novel", "poet", "theater", "cinema"],
    "biography": ["birth", "death", "people", "person", "biograph", "living people", "alumni"],
    "education": ["educat", "universit", "school", "college", "academ"],
    "india": ["india", "kerala", "tamil", "hindi", "bengal", "mumbai", "delhi", "malay", "karnatak"],
    "politics": ["politic", "govern", "election", "parliament", "president", "minister"],
    "sports": ["sport", "football", "cricket", "basketball", "olympic", "athlet", "soccer"],
    "environment": ["environ", "climate", "conserv", "species", "wildlife", "ocean", "forest"],
}


def _wiki_get(params, retries=3):
    params = {**params, "format": "json"}
    for attempt in range(retries):
        r = session.get(WIKI_API, params=params, timeout=15)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 2)) * (attempt + 1)
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("MediaWiki API rate-limited us after retries")


def fetch_contribs(username, limit=15000):
    """Paginated action=query&list=usercontribs, 500/batch (API hard cap), up to `limit` total."""
    all_contribs = []
    cont = None
    while len(all_contribs) < limit:
        params = {
            "action": "query",
            "list": "usercontribs",
            "ucuser": username,
            "uclimit": 500,
            "ucprop": "title|timestamp|comment|sizediff|tags|size|ids",
            "ucdir": "older",
        }
        if cont:
            params["uccontinue"] = cont
        data = _wiki_get(params)
        batch = (data.get("query") or {}).get("usercontribs") or []
        if not batch:
            break
        all_contribs.extend(batch)
        cont = (data.get("continue") or {}).get("uccontinue")
        if not cont:
            break
        time.sleep(0.25)
    if not all_contribs:
        raise ValueError(f'No edits found for "{username}".')
    return all_contribs[:limit]


def classify_edit(comment, tags, sizediff):
    """Mirrors classifyEdit() from the original JS."""
    c = (comment or "").lower()
    tags = tags or []
    if any(t in ("mw-rollback", "mw-undo", "mw-manual-revert") for t in tags):
        return "revert"
    if re.search(r"\bstub", c):
        return "stub_work"
    if re.search(r"copyedit|copy edit|grammar|spelling|typo", c):
        return "copyedit"
    if re.search(r"categor|recat", c):
        return "categorization"
    if re.search(r"\bref|citation|source|\bcite\b", c):
        return "references"
    if re.search(r"image|file:|photo", c):
        return "media"
    if re.search(r"infobox|template|navbox", c):
        return "template"
    if re.search(r"creat|new article", c):
        return "creation"
    if re.search(r"wikidata|wikilink|interwiki", c):
        return "wikilinks"
    if re.search(r"\blink|orphan|dead.?end", c):
        return "linking"
    if re.search(r"short desc", c):
        return "shortdesc"
    if re.search(r"merge|redirect", c):
        return "merge"
    if re.search(r"disambig|dab", c):
        return "disambig"
    if (sizediff or 0) > 500:
        return "major_add"
    if (sizediff or 0) < -500:
        return "major_remove"
    if abs(sizediff or 0) < 50:
        return "minor"
    return "general"


def fetch_categories(titles):
    """Batches of 50, mirrors fetchCategories()."""
    cat_map = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        data = _wiki_get({
            "action": "query",
            "titles": "|".join(batch),
            "prop": "categories",
            "cllimit": "max",
            "clshow": "!hidden",
        })
        pages = (data.get("query") or {}).get("pages") or {}
        for pg in pages.values():
            title = pg.get("title")
            if not title:
                continue
            cat_map[title] = [c["title"].replace("Category:", "") for c in pg.get("categories", [])]
        time.sleep(0.25)
    return cat_map


def extract_topics(cat_map):
    scores = {}
    for cats in cat_map.values():
        for cat in cats:
            cl = cat.lower()
            for topic, keywords in TOPIC_KW.items():
                if any(kw in cl for kw in keywords):
                    scores[topic] = scores.get(topic, 0) + 1
    return scores


def build_profile(username, contribs, cat_map):
    """Trimmed buildDeepProfile() — v1 scope only."""
    articles = [c for c in contribs if (c.get("ns") or 0) == 0]
    unique_articles = list({c["title"] for c in articles})

    edit_types = {}
    for c in contribs:
        t = classify_edit(c.get("comment"), c.get("tags"), c.get("sizediff"))
        edit_types[t] = edit_types.get(t, 0) + 1

    topics = extract_topics(cat_map)
    top_topics = [t[0] for t in sorted(topics.items(), key=lambda kv: kv[1], reverse=True)[:3]]
    if not top_topics:
        top_topics = ["general"]

    return {
        "username": username,
        "total": len(contribs),
        "uniqueArticles": len(unique_articles),
        "editTypes": edit_types,
        "topTopics": top_topics,
    }