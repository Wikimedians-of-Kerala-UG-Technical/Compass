from services import profile_service as ps


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
