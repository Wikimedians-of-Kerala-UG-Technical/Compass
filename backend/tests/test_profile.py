import pytest

from services import profile_service as ps, wiki


def test_classify_edit_uses_tags_first():
    assert ps.classify_edit({'tags': ['mw-rollback'], 'comment': 'typo'}) == 'revert'
    assert ps.classify_edit({'tags': ['contenttranslation-v2']}) == 'translation'
    assert ps.classify_edit({'tags': ['newcomer task copyedit']}) == 'newcomer_task'
    assert ps.classify_edit({'ns': 1}) == 'discussion'
    assert ps.classify_edit({'ns': 14}) == 'categorization'


def test_classify_edit_from_summary_and_size():
    assert ps.classify_edit({'comment': 'fixed typo'}) == 'copyedit'
    assert ps.classify_edit({'comment': 'added citation'}) == 'references'
    assert ps.classify_edit({'new': True}) == 'creation'
    assert ps.classify_edit({'sizediff': 2000}) == 'major_add'
    assert ps.classify_edit({'sizediff': -2000}) == 'major_remove'
    assert ps.classify_edit({'sizediff': 10}) == 'minor'


def test_reverted_by_others_ignores_self_reverts():
    contribs = [  # newest first, as the API returns them
        {'title': 'A', 'tags': ['mw-undo']},          # the user undid their own edit below
        {'title': 'A', 'tags': ['mw-reverted']},
        {'title': 'B', 'tags': ['mw-reverted']},      # reverted by someone else
        {'title': 'C', 'tags': []},
    ]
    assert ps.reverted_by_others(contribs) == {'count': 1, 'of': 4, 'share': 0.25}


def test_article_weight_rewards_repeat_edits_and_writing():
    assert ps.article_weight(1, 0) == 1
    assert ps.article_weight(4, 0) == 3
    assert ps.article_weight(1, 9900) == 2.0  # 10 kB written ~ one doubling of edits
    assert ps.article_weight(1, 9900) > ps.article_weight(1, 50)


def test_build_profile_rejects_blank_name():
    import pytest
    from services.wiki import UserError
    with pytest.raises(UserError):
        ps.build_profile('   ')


def _global_user(**wikis):
    return {'name': 'Akash A', 'editcount': sum(wikis.values()), 'wikis': {
        db: {'dbname': db, 'editcount': n, 'url': 'https://' + wiki.host(db)} for db, n in wikis.items()}}


def test_no_edits_message_points_to_other_projects():
    gu = _global_user(metawiki=8, commonswiki=2, enwiki=1)
    msg = ps.no_edits_message(gu, 'enwiki')
    assert msg.startswith('"Akash A" has no Wikipedia edits Compass can read yet')
    assert 'meta.wikimedia.org (8), commons.wikimedia.org (2)' in msg
    assert 'en.wikipedia.org' not in msg


def test_no_edits_message_for_a_chosen_wiki():
    gu = _global_user(enwiki=500, mlwiki=40)
    assert ps.no_edits_message(gu, 'tawiki', chosen=True) == \
        '"Akash A" has no edits on ta.wikipedia.org. Their edits are on en.wikipedia.org (500), ml.wikipedia.org (40).'


def test_suggest_username_tries_capitalisation(monkeypatch):
    asked = []
    existing = {'Akash A': 'Akash A', 'Netha Hussain': 'Netha Hussain'}
    monkeypatch.setattr(ps, '_account_exists', lambda name: asked.append(name) or existing.get(name))
    assert ps.suggest_username('Akash a') == 'Akash A'
    assert ps.suggest_username('NETHA HUSSAIN') == 'Netha Hussain'
    asked.clear()
    assert ps.suggest_username('Nobody here') is None
    assert asked == ['Nobody Here']  # the other variants are the name itself or a repeat


def test_missing_account_error_carries_the_suggestion(client, monkeypatch):
    monkeypatch.setattr(ps.wiki, 'api', lambda dbname, params, **kw: {'query': {'globaluserinfo': {'missing': True}}})
    monkeypatch.setattr(ps, '_account_exists', lambda name: 'Akash A' if name == 'Akash A' else None)
    r = client.get('/api/profile/akash_a')
    assert r.status_code == 404
    assert r.get_json() == {'error': 'No Wikimedia account named "Akash a". Did you mean "Akash A"?',
                            'suggestion': 'Akash A'}


def test_opt_out_page_blocks_the_dashboard(monkeypatch):
    ps._opt_outs._data.clear()
    asked = []

    def pages(dbname, titles, params, batch=50):
        asked.append((dbname, titles[0]))
        return iter([{'title': titles[0]}] if 'Private' in titles[0] else [{'title': titles[0], 'missing': True}])
    monkeypatch.setattr(ps.wiki, 'api_pages', pages)
    assert not ps.opted_out('Netha Hussain')
    with pytest.raises(wiki.UserError) as e:
        ps.build_profile('private_person')
    assert e.value.status == 403 and 'User:Private_person/Compass-opt-out' in str(e.value)
    assert asked == [('metawiki', 'User:Netha Hussain/Compass-opt-out'), ('metawiki', 'User:Private person/Compass-opt-out')]
