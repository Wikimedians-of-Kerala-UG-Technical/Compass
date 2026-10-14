# Test cohort

The cohort is designed to cover every kind of editor Compass claims to serve. When you change it, keep at least one user in each **segment**. A tool that only works for prolific English-Wikipedia editors should fail visibly here.

## Core users (keep stable across runs)

| User | Segment(s) | Home wiki (2026-10-13) | Why |
|---|---|---|---|
| Ranjithsiji | Indic, non-enwiki home, Commons/Wikidata heavy | wikidatawiki → mlwiki for articles | Requested; Kerala community |
| Netha Hussain | Indic, medicine, multi-project | wikidatawiki; enwiki + mlwiki articles | Requested; physician, women in science |
| Athulvis | Indic, Wikidata-only, almost no enwiki (46 edits) | wikidatawiki | Requested; stress-tests "enwiki-only" assumptions |
| Satdeep Gill | Indic (Punjabi) | pawiki | Non-Malayalam Indic language |
| Ravidreams | Indic (Tamil) | tawiki | Small enwiki footprint, big home wiki |
| Titodutta | India, enwiki-centric | enwiki | Indian editor who mainly writes in English |
| Olaniyan Olushola | Africa (Nigeria), Yoruba | enwiki / wikidatawiki | Regional coverage outside South Asia |
| Bobbyshabangu | Africa (South Africa), siSwati / isiZulu | enwiki + sswiki | Small-language Wikipedias |
| Ainali | Europe (Sweden), Wikidata | svwiki / wikidatawiki | Non-English European |
| Doc James | Global, medicine, very prolific, patroller | enwiki | Topic specialist and heavy reverter (tests `qualityTier`) |
| Rosiestep | Global, biographies of women (Women in Red) | enwiki | Content creator with a campaign focus |
| Hog Farm | Niche enwiki specialist (US Civil War, FA writer) | enwiki | Monolingual, deep niche |
| Cwmhiraeth | Niche enwiki specialist (marine invertebrates) | enwiki | Monolingual; topic missing from Compass's keyword list |

## Rotating users (refresh every run)

| Slot | How to pick |
|---|---|
| Newcomer A | `python eval/verify.py newcomers`: an account with 40–400 edits, registered within ~2 months, currently making Growth "newcomer task" edits |
| Newcomer B | Same, ideally with a different editing pattern from Newcomer A |

**Always anonymise newcomers** in reports and committed metrics.

## Optional additions
- A Wikidata-only or Commons-only editor with *no* Wikipedia articles, to check graceful degradation.
- An editor from Latin America or East Asia, to widen regional coverage.
- A non-existent username and a username with special characters (`/`, `&`, Unicode), as error-path checks.
