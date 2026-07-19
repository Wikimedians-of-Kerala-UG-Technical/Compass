import httpx
import re
import urllib.parse
import os
import asyncio
import time

# Configure robust session
def get_client():
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
    return httpx.AsyncClient(
        headers={'User-Agent': 'WikiTaskPro/1.0 (Python/ContributorC; ContributorC@wikitaskpro.local) - API Backend'},
        limits=limits,
        timeout=5.0
    )

WIKI_API_URL = "https://en.wikipedia.org/w/api.php"

# Simple manual caches for async functions
_cache_analyze = {}
_cache_analyze_light = {}
_cache_find_refs = {}
_cache_ext_refs = {}

async def analyze_article(title):
    if title in _cache_analyze: return _cache_analyze[title]
    
    if os.environ.get("STRESS_TEST") == "1":
        await asyncio.sleep(0.1)
        return {
            "title": title, "articleType": "general", "sections": [{"name": "History", "level": 2, "index": "1", "charCount": 500, "status": "ok", "refCount": 5}],
            "missingExpected": ["Description", "References"], "suggestions": [], "currentSize": 5000, "totalRefs": 5, "hasInfobox": True, "hasImages": True, "cats": ["general"]
        }

    params = {"action": "parse", "page": title, "prop": "sections|wikitext|categories", "redirects": "true", "format": "json"}
    try:
        async with get_client() as client:
            response = await client.get(WIKI_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:
        return {"title": title, "articleType": "general", "sections": [], "missingExpected": [], "suggestions": [{"type": "error", "text": "Wikipedia API failure"}], "currentSize": 0, "totalRefs": 0, "hasInfobox": False, "hasImages": False, "cats": [], "error": str(e)}
    
    if "parse" not in data:
        return {"error": "Article not found", "title": title}
        
    parse_data = data["parse"]
    raw_sections = parse_data.get("sections", [])
    wt = parse_data.get("wikitext", {}).get("*", "")
    raw_cats = parse_data.get("categories", [])
    
    sections = [{"name": s["line"], "level": int(s["level"]), "index": s["index"]} for s in raw_sections]
    cats = [c["*"].lower() for c in raw_cats if "*" in c]
    current_size = len(wt)
    
    is_bio = any("living people" in c or "deaths" in c or "births" in c for c in cats)
    is_med = any("disease" in c or "medic" in c or "drug" in c or "syndrome" in c for c in cats)
    is_place = any("city" in c or "village" in c or "district" in c for c in cats)
    is_event = any("event" in c or "war" in c or "election" in c for c in cats)
    
    if is_bio: expected = ['Early life', 'Career', 'Personal life', 'Awards', 'Legacy', 'References']; article_type = 'biography'
    elif is_med: expected = ['Signs and symptoms', 'Causes', 'Diagnosis', 'Treatment', 'Epidemiology', 'References']; article_type = 'medical'
    elif is_place: expected = ['History', 'Geography', 'Demographics', 'Economy', 'References']; article_type = 'place'
    elif is_event: expected = ['Background', 'Timeline', 'Aftermath', 'Reactions', 'References']; article_type = 'event'
    else: expected = ['History', 'Description', 'References']; article_type = 'general'
        
    existing_sections = [s["name"].lower() for s in sections]
    missing_expected = [e for e in expected if not any(e.lower() in ex for ex in existing_sections)]
    
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
    if not has_infobox: suggestions.append({"type": "structure", "text": "Add an infobox"})
    if not has_images: suggestions.append({"type": "media", "text": "Add images from Wikimedia Commons"})
    if total_refs < 3: suggestions.append({"type": "refs", "text": f"Very few references ({total_refs}) — needs sourcing"})
    for s in missing_expected: suggestions.append({"type": "section", "text": f'Add "{s}" section'})
    for s in sections:
        if s["status"] == "short" and s["name"] not in ("References", "External links"):
            suggestions.append({"type": "expand", "text": f'Expand "{s["name"]}" — very short ({s["charCount"]} chars)'})
        if s["refCount"] == 0 and s["charCount"] > 200 and s["name"] not in ("See also", "External links"):
            suggestions.append({"type": "refs", "text": f'Add refs to "{s["name"]}" — no citations'})
            
    res = {"title": title, "articleType": article_type, "sections": sections, "missingExpected": missing_expected, "suggestions": suggestions, "currentSize": current_size, "totalRefs": total_refs, "hasInfobox": has_infobox, "hasImages": has_images, "cats": cats}
    _cache_analyze[title] = res
    return res

async def analyze_article_light(title):
    if title in _cache_analyze_light: return _cache_analyze_light[title]
    if os.environ.get("STRESS_TEST") == "1":
        await asyncio.sleep(0.05)
        return {"missingExpected": ["Description", "References"], "suggestions": [{"type": "section", "text": "Add Description section"}]}

    params = {"action": "parse", "page": title, "prop": "sections|categories|templates", "redirects": "true", "format": "json"}
    try:
        async with get_client() as client:
            response = await client.get(WIKI_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError:
        return {"missingExpected": [], "suggestions": [{"type": "error", "text": "API Failure"}]}
        
    if "parse" not in data: return {"missingExpected": [], "suggestions": []}
        
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
    
    if is_bio: expected = ['Early life', 'Career', 'Personal life', 'Awards', 'Legacy', 'References']
    elif is_med: expected = ['Signs and symptoms', 'Causes', 'Diagnosis', 'Treatment', 'Epidemiology', 'References']
    elif is_place: expected = ['History', 'Geography', 'Demographics', 'Economy', 'References']
    elif is_event: expected = ['Background', 'Timeline', 'Aftermath', 'Reactions', 'References']
    else: expected = ['History', 'Description', 'References']
        
    existing_sections = [s["name"].lower() for s in sections]
    missing_expected = [e for e in expected if not any(e.lower() in ex for ex in existing_sections)]
    
    has_infobox = any("infobox" in t.get("*", "").lower() for t in raw_templates)
    
    suggestions = []
    if not has_infobox: suggestions.append({"type": "structure", "text": "Add an infobox"})
    for s in missing_expected: suggestions.append({"type": "section", "text": f'Add "{s}" section'})
        
    res = {"missingExpected": missing_expected, "suggestions": suggestions}
    _cache_analyze_light[title] = res
    return res

async def _process_single_reference(item, original_title):
    if item["title"].lower() == original_title.lower(): return None
    analysis = await analyze_article_light(item["title"])
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

async def find_references(title, offset=0):
    cache_key = f"{title}_{offset}"
    if cache_key in _cache_find_refs: return _cache_find_refs[cache_key]

    if os.environ.get("STRESS_TEST") == "1":
        await asyncio.sleep(0.2)
        fake_results = [{"title": f"Fake_Ref_{i}", "timestamp": "2024-01-01T00:00:00Z", "wordcount": 1000} for i in range(5)]
        tasks = [_process_single_reference(res, title) for res in fake_results]
        results = await asyncio.gather(*tasks)
        refs = [res for res in results if res is not None]
        return {"results": refs, "nextOffset": int(offset) + 5, "total": 10000}

    search_params = {"action": "query", "list": "search", "srsearch": title, "utf8": "1", "format": "json", "srlimit": 15, "sroffset": offset}
    try:
        async with get_client() as client:
            r = await client.get(WIKI_API_URL, params=search_params)
            r.raise_for_status()
            data = r.json()
        search_results = data.get("query", {}).get("search", [])
        
        tasks = [_process_single_reference(res, title) for res in search_results]
        results = await asyncio.gather(*tasks)
        
        refs = [res for res in results if res is not None]
        next_offset = data.get("continue", {}).get("sroffset")
        total_hits = data.get("query", {}).get("searchinfo", {}).get("totalhits", 0)
        
        res = {"results": refs, "nextOffset": next_offset, "total": total_hits}
        _cache_find_refs[cache_key] = res
        return res
    except Exception as e:
        return {"results": [], "nextOffset": None, "total": 0, "error": str(e)}

async def fetch_semantic_scholar(title):
    try:
        async with get_client() as client:
            r = await client.get("https://api.semanticscholar.org/graph/v1/paper/search", params={"query": title, "limit": 10, "fields": "title,url,citationCount"})
            if r.status_code == 200:
                return [{"title": p.get("title"), "url": p.get("url"), "citations": p.get("citationCount"), "source": "Semantic Scholar"} for p in r.json().get("data", [])]
    except Exception: pass
    return []

async def fetch_crossref(title):
    try:
        async with get_client() as client:
            r = await client.get("https://api.crossref.org/works", params={"query.bibliographic": title, "select": "title,URL,is-referenced-by-count", "rows": 10})
            if r.status_code == 200:
                return [{"title": p.get("title", [""])[0], "url": p.get("URL"), "citations": p.get("is-referenced-by-count"), "source": "CrossRef"} for p in r.json().get("message", {}).get("items", [])]
    except Exception: pass
    return []

MEDICAL_HINTS = ('medic', 'disease', 'health', 'hospital', 'drug', 'pharma', 'anatom', 'surg', 'radiol', 'pathol', 'diagnos', 'therap', 'clinic', 'symptom', 'syndrome', 'cancer', 'infect', 'epidem', 'virus', 'bacter', 'vaccine')

async def fetch_pubmed(title):
    try:
        async with get_client() as client:
            r = await client.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params={"db": "pubmed", "term": title, "retmode": "json", "retmax": 10})
            if r.status_code == 200:
                ids = r.json().get("esearchresult", {}).get("idlist", [])
                if ids:
                    r2 = await client.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi", params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"})
                    if r2.status_code == 200:
                        data = r2.json().get("result", {})
                        return [{"title": data[uid].get("title"), "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/", "citations": 0, "source": "PubMed"} for uid in ids if uid in data]
    except Exception: pass
    return []

async def find_external_references(title):
    if title in _cache_ext_refs: return _cache_ext_refs[title]
    is_medical = any(kw in title.lower() for kw in MEDICAL_HINTS)
    
    tasks = [fetch_semantic_scholar(title), fetch_crossref(title)]
    if is_medical: tasks.append(fetch_pubmed(title))
    
    results = await asyncio.gather(*tasks)
    sources = [results[0], results[1], results[2] if is_medical else []]
    
    merged = []
    for i in range(max((len(s) for s in sources), default=0)):
        for s in sources:
            if i < len(s): merged.append(s[i])
            
    seen = set()
    deduped = []
    for r in merged:
        t = r.get("title") or ""
        tl = t.lower().strip()
        if tl and tl not in seen:
            seen.add(tl)
            deduped.append(r)
            
    res = {"results": deduped}
    _cache_ext_refs[title] = res
    return res
