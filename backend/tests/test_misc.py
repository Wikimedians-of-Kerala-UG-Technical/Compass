from services import ratelimit, references_service as refs


def test_rate_limiter_window():
    rl = ratelimit.RateLimiter(2, 60)
    assert rl.check('a', now=0) == 0
    assert rl.check('a', now=1) == 0
    assert rl.check('a', now=2) == 59
    assert rl.check('b', now=2) == 0
    assert rl.check('a', now=61) == 0


def test_rate_limit_parse():
    assert ratelimit.parse('120/minute') == (120, 60)
    assert ratelimit.parse('5/second') == (5, 1)
    assert ratelimit.parse('0') is None and ratelimit.parse('') is None


def test_cite_template_journal():
    item = {'itemType': 'journalArticle', 'title': 'TB review', 'publicationTitle': 'Lancet', 'date': '2024',
            'author': [['Ann', 'Lee'], ['', 'WHO']], 'DOI': '10.1/x', 'ISSN': ['1234-5678']}
    t = refs.cite_template(item)
    assert t.startswith('{{cite journal |last1=Lee |first1=Ann |last2=WHO |title=TB review |journal=Lancet')
    assert '|doi=10.1/x' in t and 'url=' not in t


def test_cite_template_book_uses_first_isbn():
    t = refs.cite_template({'itemType': 'book', 'title': 'Kerala', 'publisher': 'DC Books',
                            'ISBN': ['9788126400000 8126400000']})
    assert t == '{{cite book |title=Kerala |publisher=DC Books |isbn=9788126400000}}'


def test_relevance_filters():
    assert refs._relevant({'title': 'Founding of Sahitya Akademi'}, 'Kerala Sahitya Akademi')
    assert refs._relevant_strict({'title': 'Anthill (Winner of Kerala Sahitya Akademi Award)'}, 'Kerala Sahitya Akademi')
    assert not refs._relevant_strict({'title': 'Kerala Varma'}, 'Kerala Sahitya Akademi')
    assert refs._relevant_strict({'title': 'Tuberculosis'}, 'Tuberculosis')


def test_doi_extraction():
    assert refs._doi('https://doi.org/10.1016/S0140-6736(24)00001-X.') == '10.1016/s0140-6736(24)00001-x'
    assert refs._doi('no doi here') is None
