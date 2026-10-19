# Feature: Article Guide and Sources

**Endpoints:** `GET /api/article/<title>/guide[?wiki=]`, `GET /api/article/<title>/external-references[?wiki=]`
**Services:** `services/article_service.py`, `services/references_service.py`
**UI:** Guide (top-bar search, or "What exactly needs fixing?" on any task)

Answers: *where exactly is the problem in this article, and what can I cite?*

---

## Guide: reading the article like Wikipedia does

The guide fetches **Parsoid HTML** (`/w/rest.php/v1/page/<title>/html`). Every section is a `<section data-mw-section-id>`, every citation is a `sup.mw-ref`, and every template carries its name and parameters in `data-mw`. v1 split wikitext on `==` with regexes. Its "very short" warnings were false alarms on long articles: *Tuberculosis* got "Expand 'Causes' — 2 chars".

| Finding | How |
|---|---|
| **Uncited paragraphs** | Paragraphs of ≥ 150 characters with no citation, outside reference, list and filmography sections. The suggestion quotes the paragraph's first words. |
| **Inline tags with dates** | Templates such as `{{Citation needed|date=July 2026}}`, `{{Dead link}}`, `{{Failed verification}}` and `{{Clarify}}`, found by name in `data-mw`. On other wikis the names are mapped from English (ml: `തെളിവ്`). Each tag comes with the sentence it sits in. |
| Banner tags with dates | Dated hidden tracking categories ("Articles needing additional references (tagged 2022-04)") |
| Dead links | `{{Dead link}}`, plus citations with `url-status=dead` and no archive |
| Bare URLs | Free-text external links in the reference list |
| Short lead | Lead < 250 characters in an article over 3,000 characters |
| Image to add | No images in the article, but Wikidata has P18 (thumbnail shown) or a Commons category (P373) |
| Missing sections | Non-English articles: sections the English article has that this one lacks, with the heading translated, from cxserver `/v2/suggest/sections/<en title>/en/<lang>`. Each links to Content Translation. |
| Facts | Wikidata birth date whose year doesn't appear in the article |
| Quality | PageAssessments class and importance, plus what the next class needs |

## Sources (external references)

| Step | Detail |
|---|---|
| Topic routing | The article's ML topics decide the sources. Medicine & Health or Biology add **PubMed review articles from the last 10 years** (WP:MEDRS). Everything gets OpenAlex and CrossRef. v1 triggered PubMed on title words, so *Tuberculosis* never got PubMed. |
| Query | The English title (via langlinks for other wikis), without its disambiguator ("Dosa (food)" → "Dosa") |
| Noise filter | CrossRef results below relevance score 20 are dropped (v1 returned "NEUTRINOS AT LAKE LOUISE" for *Lake Louise criteria*) |
| Already cited | DOIs found in the article's citations are excluded |
| Ready to paste | Each result with a DOI or PMID goes through **Citoid**, the service behind VisualEditor's Cite button. It becomes `{{cite journal |last1=… |first1=… |title=… |journal=… |date=… |volume=… |pages=… |doi=… |pmid=…}}`, with a Copy button. |
| Semantic Scholar | Used only when `SEMANTIC_SCHOLAR_API_KEY` is set. Without a key, every call returns HTTP 429. |
| Books and archives | Articles that aren't medical also search **Open Library** and the **Internet Archive** (searched as a phrase; the Digital Library of India collection is there), and **Google Books** when `GOOGLE_BOOKS_API_KEY` is set (the anonymous quota is always used up). Catalogue results must share at least two significant words with the article title, and archive results one: "Kerala Sahitya Akademi" otherwise gets *Kerala Varma*, and books the Akademi *published*. Books are cited by ISBN and archive items by URL, both through Citoid. |

The v1 "Wikipedia references" list was removed. It suggested other Wikipedia articles as sources, which Wikipedia doesn't allow (WP:CIRCULAR).
