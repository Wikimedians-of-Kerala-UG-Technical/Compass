from services import signals


def test_topic_slug_and_label():
    assert signals.topic_slug('Culture.Media.Films') == 'films'
    assert signals.topic_slug('STEM.Medicine_&_Health') == 'medicine-and-health'
    assert signals.topic_label('Geography.Regions.Asia.South_Asia') == 'South Asia'
    assert signals.is_region_topic('Geography.Regions.Asia.South_Asia')


def test_dated_tags_keeps_earliest_month():
    cats = ['Articles needing additional references from April 2022',
            'Articles needing additional references from January 2021',
            'Articles with unsourced statements from July 2026', 'Living people', 'Foo from Smarch 2020']
    assert signals.dated_tags(cats) == {
        'Articles needing additional references': '2021-01',
        'Articles with unsourced statements': '2026-07',
    }


def test_aggregate_profile_weights():
    sigs = [{'topics': {'A': 1.0}, 'countries': {'India': 0.5}}, {'topics': {'A': 0.5, 'B': 1.0}, 'countries': {}}]
    topics, countries = signals.aggregate_profile(sigs, [2, 1])
    assert topics == {'A': 2.5, 'B': 1.0}
    assert countries == {'India': 1.0}


def test_parse_doc():
    page = {'title': 'Kochi', 'cirrusdoc': [{'source': {
        'weighted_tags': ['classification.prediction.articletopic/Geography.Regions.Asia.South_Asia|870',
                          'classification.prediction.articlecountry/India|990',
                          'recommendation.image/exists|1'],
        'popularity_score': 1e-6, 'text_bytes': 1200,
        'coordinates': [{'primary': True, 'globe': 'earth', 'coord': {'lat': 9.9, 'lon': 76.2}}],
        'category': ['Cities in Kerala'], 'template': ['Template:Infobox settlement'],
    }}]}
    sig = signals._parse_doc(page)
    assert sig['topics'] == {'Geography.Regions.Asia.South_Asia': 0.87}
    assert sig['countries'] == {'India': 0.99}
    assert sig['recommendations'] == ['image']
    assert sig['coord'] == {'lat': 9.9, 'lon': 76.2}
    assert sig['templates'] == ['Infobox settlement']
    assert signals._parse_doc({'title': 'X'}) is None


def test_country_info():
    assert signals.country_info('India')['a3'] == 'ind'  # the form articlecountry: takes
    assert signals.country_info('Atlantis') is None
