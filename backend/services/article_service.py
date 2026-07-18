import requests
import re
import urllib.parse
import os
import time
from concurrent.futures import ThreadPoolExecutor
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import functools

"""
JSON Output Contracts:

1. analyze_article(title) -> dict
{
    "title": string,
    "articleType": string ("biography", "medical", "place", "event", "general"),
    "sections": [
        {"name": string, "level": int, "index": string, "charCount": int, "status": "short"|"ok", "refCount": int}
    ],
    "missingExpected": [string],
    "suggestions": [
        {"type": string, "text": string}
    ],
    "currentSize": int,
    "totalRefs": int,
    "hasInfobox": boolean,
    "hasImages": boolean,
    "cats": [string]
}

2. find_references(title, offset) -> dict
{
    "results": [
        {
            "title": string,
            "authors": string,
            "year": string,
            "venue": string,
            "url": string,
            "citations": int|null,
            "source": string,
            "doi": string,
            "whatToEdit": [{"type": string, "text": string}],
            "missingSections": [string]
        }
    ],
    "nextOffset": int|null,
    "total": int
}
"""

# Configure robust session with professional retry strategy and throttling handling
_local_session = None

def get_session():
    global _local_session
    if _local_session is None:
        _local_session = requests.Session()
        # Wikipedia requires a highly descriptive User-Agent
        _local_session.headers.update({'User-Agent': 'WikiTaskPro/1.0 (Python/ContributorC; ContributorC@wikitaskpro.local) - API Backend'})
        
        # Retry strategy: exponential backoff + handling 429 Too Many Requests
        retry_strategy = Retry(
            total=4,  # Max retries
            backoff_factor=1.5,  # 1.5s, 3s, 6s...
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            respect_retry_after_header=True
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        _local_session.mount("https://", adapter)
        _local_session.mount("http://", adapter)
    return _local_session

WIKI_API_URL = "https://en.wikipedia.org/w/api.php"

@functools.lru_cache(maxsize=128)
def analyze_article(title):
    """
    Port of analyzeArticle from index.html
    Fetches wikitext, sections, and categories to build a guide.
    """
    
    # STRESS TEST MOCK (Prevents Wikipedia IP Ban)
    if os.environ.get("STRESS_TEST") == "1":
        time.sleep(0.1) # Simulate 100ms network latency
        return {
            "title": title,
            "articleType": "general",
            "sections": [{"name": "History", "level": 2, "index": "1", "charCount": 500, "status": "ok", "refCount": 5}],
            "missingExpected": ["Description", "References"],
            "suggestions": [],
            "currentSize": 5000,
            "totalRefs": 5,
            "hasInfobox": True,
            "hasImages": True,
            "cats": ["general"]
        }

    params = {
        "action": "parse",
        "page": title,
        "prop": "sections|wikitext|categories",
        "redirects": "true",
        "format": "json"
    }
    
    try:
        response = get_session().get(WIKI_API_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        # Wikipedia API failed (e.g. 429 exhausted or timeout), return safe response
        return {
            "title": title,
            "articleType": "general",
            "sections": [],
            "missingExpected": [],
            "suggestions": [{"type": "error", "text": "Wikipedia API failure (Timeout or Rate Limit)"}],
            "currentSize": 0,
            "totalRefs": 0,
            "hasInfobox": False,
            "hasImages": False,
            "cats": [],
            "error": str(e)
        }
    
    if "parse" not in data:
        return {"error": "Article not found", "title": title}
        
    parse_data = data["parse"]
    raw_sections = parse_data.get("sections", [])
    wt = parse_data.get("wikitext", {}).get("*", "")
    raw_cats = parse_data.get("categories", [])
    
    sections = [{"name": s["line"], "level": int(s["level"]), "index": s["index"]} for s in raw_sections]
    cats = [c["*"].lower() for c in raw_cats if "*" in c]
    current_size = len(wt)
    
    # Determine article type
    is_bio = any("living people" in c or "deaths" in c or "births" in c for c in cats)
    is_med = any("disease" in c or "medic" in c or "drug" in c or "syndrome" in c for c in cats)
    is_place = any("city" in c or "village" in c or "district" in c for c in cats)
    is_event = any("event" in c or "war" in c or "election" in c for c in cats)
    
    if is_bio:
        expected = ['Early life', 'Career', 'Personal life', 'Awards', 'Legacy', 'References']
        article_type = 'biography'
    elif is_med:
        expected = ['Signs and symptoms', 'Causes', 'Diagnosis', 'Treatment', 'Epidemiology', 'References']
        article_type = 'medical'
    elif is_place:
        expected = ['History', 'Geography', 'Demographics', 'Economy', 'References']
        article_type = 'place'
    elif is_event:
        expected = ['Background', 'Timeline', 'Aftermath', 'Reactions', 'References']
        article_type = 'event'
    else:
        expected = ['History', 'Description', 'References']
        article_type = 'general'
        
    existing_sections = [s["name"].lower() for s in sections]
    missing_expected = [e for e in expected if not any(e.lower() in ex for ex in existing_sections)]
    
    # Section text splitting
    s_texts = re.split(r'^=+[^=]+=+$', wt, flags=re.MULTILINE)
    
    for i, s in enumerate(sections):
        t = s_texts[i + 1] if (i + 1) < len(s_texts) else ""
        s["charCount"] = len(t)
        s["status"] = "short" if len(t) < 200 else "ok"
        s["refCount"] = len(re.findall(r'<ref', t, flags=re.IGNORECASE))
        
    total_refs = len(re.findall(r'<ref', wt, flags=re.IGNORECASE))
    has_infobox = bool(re.search(r'\{\{[Ii]nfobox', wt))
    has_images = bool(re.search(r'\[\[File:|\[\[Image:', wt))
    
    suggestions = []
    if not has_infobox:
        suggestions.append({"type": "structure", "text": "Add an infobox"})
    if not has_images:
        suggestions.append({"type": "media", "text": "Add images from Wikimedia Commons"})
    if total_refs < 3:
        suggestions.append({"type": "refs", "text": f"Very few references ({total_refs}) — needs sourcing"})
        
    for s in missing_expected:
        suggestions.append({"type": "section", "text": f'Add "{s}" section'})
        
    for s in sections:
        if s["status"] == "short" and s["name"] not in ("References", "External links"):
            suggestions.append({"type": "expand", "text": f'Expand "{s["name"]}" — very short ({s["charCount"]} chars)'})
        if s["refCount"] == 0 and s["charCount"] > 200 and s["name"] not in ("See also", "External links"):
            suggestions.append({"type": "refs", "text": f'Add refs to "{s["name"]}" — no citations'})
            
    return {
        "title": title,
        "articleType": article_type,
        "sections": sections,
        "missingExpected": missing_expected,
        "suggestions": suggestions,
        "currentSize": current_size,
        "totalRefs": total_refs,
        "hasInfobox": has_infobox,
        "hasImages": has_images,
        "cats": cats
    }

@functools.lru_cache(maxsize=128)
def analyze_article_light(title):
    """
    Lightweight version of analyze_article for sub-references.
    Skips the heavy wikitext download (requests templates/categories/sections only).
    """
    if os.environ.get("STRESS_TEST") == "1":
        time.sleep(0.05)
        return {"missingExpected": ["Description", "References"], "suggestions": [{"type": "section", "text": "Add Description section"}]}

    params = {
        "action": "parse",
        "page": title,
        "prop": "sections|categories|templates",
        "redirects": "true",
        "format": "json"
    }
    
    try:
        response = get_session().get(WIKI_API_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException:
        return {"missingExpected": [], "suggestions": [{"type": "error", "text": "API Failure"}]}
        
    if "parse" not in data:
        return {"missingExpected": [], "suggestions": []}
        
    parse_data = data["parse"]
    raw_sections = parse_data.get("sections", [])
    raw_cats = parse_data.get("categories", [])
    raw_templates = parse_data.get("templates", [])
    
    sections = [{"name": s["line"], "level": int(s["level"])} for s in raw_sections]
    cats = [c["*"].lower() for c in raw_cats if "*" in c]
    
    is_bio = any("living people" in c or "deaths" in c or "births" in c for c in cats)
    is_med = any("disease" in c or "medic" in c or "drug" in c or "syndrome" in c for c in cats)
    is_place = any("city" in c or "village" in c or "district" in c for c in cats)
    is_event = any("event" in c or "war" in c or "election" in c for c in cats)
    
    if is_bio:
        expected = ['Early life', 'Career', 'Personal life', 'Awards', 'Legacy', 'References']
    elif is_med:
        expected = ['Signs and symptoms', 'Causes', 'Diagnosis', 'Treatment', 'Epidemiology', 'References']
    elif is_place:
        expected = ['History', 'Geography', 'Demographics', 'Economy', 'References']
    elif is_event:
        expected = ['Background', 'Timeline', 'Aftermath', 'Reactions', 'References']
    else:
        expected = ['History', 'Description', 'References']
        
    existing_sections = [s["name"].lower() for s in sections]
    missing_expected = [e for e in expected if not any(e.lower() in ex for ex in existing_sections)]
    
    has_infobox = any("infobox" in t.get("*", "").lower() for t in raw_templates)
    
    suggestions = []
    if not has_infobox:
        suggestions.append({"type": "structure", "text": "Add an infobox"})
    for s in missing_expected:
        suggestions.append({"type": "section", "text": f'Add "{s}" section'})
        
    return {
        "missingExpected": missing_expected,
        "suggestions": suggestions
    }

def _process_single_reference(item, original_title):
    if item["title"].lower() == original_title.lower():
        return None
        
    analysis = analyze_article_light(item["title"])
    
    return {
        "title": item["title"],
        "authors": "Wikipedia Contributors",
        "year": item.get("timestamp", "")[:4],
        "venue": "English Wikipedia",
        "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(item['title'].replace(' ', '_'))}",
        "citations": item.get("wordcount", 0),
        "source": "Wikipedia API",
        "doi": "",
        "whatToEdit": analysis.get("suggestions", []),
        "missingSections": analysis.get("missingExpected", [])
    }

@functools.lru_cache(maxsize=128)
def find_references(title, offset=0):
    """
    Finds references using Wikipedia API, supports pagination, 
    and analyzes each result to find what to edit and missing sections.
    """
    
    # STRESS TEST MOCK (Prevents Wikipedia IP Ban)
    if os.environ.get("STRESS_TEST") == "1":
        time.sleep(0.2) # Simulate 200ms search latency
        fake_results = [{"title": f"Fake_Ref_{i}", "timestamp": "2024-01-01T00:00:00Z", "wordcount": 1000} for i in range(5)]
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            original_titles = [title] * len(fake_results)
            results = list(executor.map(_process_single_reference, fake_results, original_titles))
            
        refs = [res for res in results if res is not None]
        return {"results": refs, "nextOffset": int(offset) + 5, "total": 10000}

    refs = []
    
    # Search Wikipedia for related articles
    search_params = {
        "action": "query",
        "list": "search",
        "srsearch": title,
        "utf8": "1",
        "format": "json",
        "srlimit": 5, # Keep it at 5 per page to avoid massive timeouts when analyzing each
        "sroffset": offset
    }
    
    try:
        r = get_session().get(WIKI_API_URL, params=search_params, timeout=5)
        r.raise_for_status()
        data = r.json()
        
        search_results = data.get("query", {}).get("search", [])
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            original_titles = [title] * len(search_results)
            results = list(executor.map(_process_single_reference, search_results, original_titles))
            
        refs = [res for res in results if res is not None]
        
        next_offset = data.get("continue", {}).get("sroffset")
        total_hits = data.get("query", {}).get("searchinfo", {}).get("totalhits", 0)
        
        return {
            "results": refs,
            "nextOffset": next_offset,
            "total": total_hits
        }
            
    except Exception as e:
        return {"results": [], "nextOffset": None, "total": 0, "error": str(e)}

def fetch_semantic_scholar(title):
    try:
        r = get_session().get("https://api.semanticscholar.org/graph/v1/paper/search", params={"query": title, "limit": 5, "fields": "title,url,citationCount"}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return [{"title": p.get("title"), "url": p.get("url"), "citations": p.get("citationCount"), "source": "Semantic Scholar"} for p in data.get("data", [])]
    except Exception: pass
    return []

def fetch_crossref(title):
    try:
        r = get_session().get("https://api.crossref.org/works", params={"query": title, "select": "title,URL,is-referenced-by-count", "sort": "is-referenced-by-count", "rows": 5}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return [{"title": p.get("title", [""])[0], "url": p.get("URL"), "citations": p.get("is-referenced-by-count"), "source": "CrossRef"} for p in data.get("message", {}).get("items", [])]
    except Exception: pass
    return []

def fetch_pubmed(title):
    try:
        r = get_session().get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params={"db": "pubmed", "term": title, "retmode": "json", "retmax": 5}, timeout=5)
        if r.status_code == 200:
            ids = r.json().get("esearchresult", {}).get("idlist", [])
            if ids:
                r2 = get_session().get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi", params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"}, timeout=5)
                if r2.status_code == 200:
                    data = r2.json().get("result", {})
                    return [{"title": data[uid].get("title"), "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/", "citations": 0, "source": "PubMed"} for uid in ids if uid in data]
    except Exception: pass
    return []

@functools.lru_cache(maxsize=128)
def find_external_references(title):
    """
    Finds references using Semantic Scholar, CrossRef, and PubMed.
    Deduplicates and sorts by citation count.
    """
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as executor:
        f1 = executor.submit(fetch_semantic_scholar, title)
        f2 = executor.submit(fetch_crossref, title)
        f3 = executor.submit(fetch_pubmed, title)
        
        results = f1.result() + f2.result() + f3.result()
        
    seen = set()
    deduped = []
    for r in results:
        t = r.get("title") or ""
        tl = t.lower().strip()
        if tl and tl not in seen:
            seen.add(tl)
            deduped.append(r)
            
    deduped.sort(key=lambda x: x.get("citations") or 0, reverse=True)
    return {"results": deduped}

