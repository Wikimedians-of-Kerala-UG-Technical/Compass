import time

from services.category_service import _wiki_get, WIKIDATA_API

MAX_HOPS = 6

HUMAN_QID = "Q5"


def _fetch_claims_batch(qids, claims_map):
    """Batched wbgetentities -- fills claims_map[qid] with the fields we need to walk
    the place hierarchy: whether it's a country (P297) or first-level admin division
    (P300), whether it's a human, and the QIDs P131/P17/P19/P27 point to.
    """
    qid_list = [q for q in qids if q and q not in claims_map]
    for i in range(0, len(qid_list), 50):
        batch = qid_list[i:i + 50]
        if not batch:
            continue
        data = _wiki_get({
            "action": "wbgetentities",
            "ids": "|".join(batch),
            "props": "claims|labels",
            "languages": "en",
        }, api_url=WIKIDATA_API)
        entities = data.get("entities") or {}
        for qid, entity in entities.items():
            claims = entity.get("claims") or {}

            def target_qids(prop):
                out = []
                for c in claims.get(prop, []):
                    try:
                        out.append(c["mainsnak"]["datavalue"]["value"]["id"])
                    except (KeyError, TypeError):
                        continue
                return out

            label = ((entity.get("labels") or {}).get("en") or {}).get("value")
            claims_map[qid] = {
                "label": label,
                "is_country": "P297" in claims,
                "is_admin1": "P300" in claims,
                "is_human": HUMAN_QID in target_qids("P31"),
                "p131": target_qids("P131"),
                "p17": target_qids("P17"),
                "p19": target_qids("P19"),
                "p27": target_qids("P27"),
            }
        time.sleep(0.25)


def _pick_anchor(qid, claims_map):
    """Picks the place to start walking the hierarchy from.

    People: their birthplace (a real, nestable place) if known, else their country of
    citizenship (country-level only, no state). Everything else: only if the article
    is itself genuinely nested in a place hierarchy (has P131), or is itself a country
    or first-level admin division -- subjects with no place-hierarchy membership at all
    (companies, films, generic organizations) contribute no geo signal, deliberately.
    """
    info = claims_map.get(qid)
    if not info:
        return None
    if info["is_human"]:
        if info["p19"]:
            return info["p19"][0]
        if info["p27"]:
            return info["p27"][0]
        return None
    if info["p131"] or info["is_country"] or info["is_admin1"]:
        return qid
    return None


def resolve_geo_chains(article_qids):
    """
    article_qids: iterable of Wikidata QIDs for the user's edited articles.

    For each article whose subject resolves to a place, walks the P131 (located-in)
    hierarchy up to `MAX_HOPS` levels, collecting every place name along the way --
    e.g. ["Kochi", "Ernakulam district", "Kerala", "India"] -- stopping once a country
    (P297) is reached. Every level is kept, not just the final country, since all of
    them are meaningful signal for recommendations.

    Returns {article_qid: [place_name, ..., country_name]}, omitting articles with no
    resolvable geography.
    """
    article_qids = list(article_qids)
    claims_map = {}
    _fetch_claims_batch(article_qids, claims_map)

    anchors = {}
    for qid in article_qids:
        anchor = _pick_anchor(qid, claims_map)
        if anchor:
            anchors[qid] = anchor

    _fetch_claims_batch(set(anchors.values()), claims_map)

    chains = {a: [] for a in set(anchors.values())}
    frontier = {a: a for a in set(anchors.values())}
    done = set()

    for _hop in range(MAX_HOPS):
        active = {a: q for a, q in frontier.items() if a not in done}
        if not active:
            break
        next_needed = set()
        for anchor, current in active.items():
            info = claims_map.get(current)
            if not info:
                done.add(anchor)
                continue
            if info["label"]:
                chains[anchor].append(info["label"])
            if info["is_country"]:
                done.add(anchor)
                continue
            parents = info["p131"] or info["p17"]
            if not parents:
                done.add(anchor)
                continue
            nxt = parents[0]
            frontier[anchor] = nxt
            next_needed.add(nxt)
        if next_needed:
            _fetch_claims_batch(next_needed, claims_map)

    result = {}
    for article_qid, anchor_qid in anchors.items():
        chain = chains.get(anchor_qid) or []
        if chain:
            result[article_qid] = chain
    return result
