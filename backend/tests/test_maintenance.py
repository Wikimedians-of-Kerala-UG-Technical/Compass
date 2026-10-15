from services import maintenance


def test_issues_of_enwiki_prefers_unreferenced(monkeypatch):
    local = {k: {'template': v['template'], 'category': v['category'], 'categoryCount': 10}
             for k, v in maintenance.ISSUES.items()}
    monkeypatch.setattr(maintenance, 'local_issues', lambda dbname: local)
    sig = {'categories': ['All articles lacking sources', 'All articles needing additional references'],
           'templates': [], 'recommendations': ['image']}
    assert maintenance.issues_of('enwiki', sig) == ['add_refs', 'add_image']


def test_issues_of_other_wikis_counts_templates(monkeypatch):
    local = {'add_citations': {'template': 'തെളിവ്', 'category': None, 'categoryCount': 0}}
    monkeypatch.setattr(maintenance, 'local_issues', lambda dbname: local)
    assert maintenance.issues_of('mlwiki', {'categories': [], 'templates': ['തെളിവ്']}) == ['add_citations']


def test_use_category_falls_back_to_template_on_sparse_wikis():
    assert maintenance.use_category('enwiki', {'category': 'X', 'template': 'Y', 'categoryCount': 3})
    assert not maintenance.use_category('mlwiki', {'category': 'X', 'template': 'Y', 'categoryCount': 500})
    assert maintenance.use_category('mlwiki', {'category': 'X', 'template': None, 'categoryCount': 5})


def test_meta_falls_back_for_unknown_keys():
    assert maintenance.meta('add_link')['minutes'] == 5
    assert maintenance.meta('mystery')['label'] == 'mystery'
