from dataclasses import replace

import pytest

from scholaros.models import AIUsePolicy, Decision, EligibilityResult
from scholaros.policy import WritingAction, submission_allowed, writing_action_allowed
from scholaros.ranking import rank_eligible
from test_eligibility import BASE, STUDENT


def test_ineligible_and_unknown_are_excluded():
    candidates = [
        (BASE, EligibilityResult(Decision.ELIGIBLE, ("verified",))),
        (replace(BASE, id="unknown"), EligibilityResult(Decision.UNKNOWN, ("missing",))),
        (replace(BASE, id="blocked"), EligibilityResult(Decision.INELIGIBLE, ("no",))),
    ]
    assert [x.opportunity.id for x in rank_eligible(STUDENT, candidates)] == ["test"]


def test_ranking_order_deterministic_on_ties():
    a = replace(BASE, id="a")
    b = replace(BASE, id="b")
    results = [(b, EligibilityResult(Decision.ELIGIBLE, ())), (a, EligibilityResult(Decision.ELIGIBLE, ()))]
    assert [x.opportunity.id for x in rank_eligible(STUDENT, results)] == ["a", "b"]


def test_invalid_weights_rejected():
    with pytest.raises(ValueError):
        rank_eligible(STUDENT, [], fit_weight=-1)
    with pytest.raises(ValueError):
        rank_eligible(STUDENT, [], fit_weight=0, value_weight=0, ease_weight=0)


def test_unknown_or_prohibited_ai_policy_blocks_drafts():
    for p in [AIUsePolicy.UNKNOWN, AIUsePolicy.PROHIBITED, AIUsePolicy.EDITING_ONLY]:
        assert not writing_action_allowed(p, WritingAction.GENERATE_DRAFT)


def test_editing_only_allows_only_editing():
    assert writing_action_allowed(AIUsePolicy.EDITING_ONLY, WritingAction.EDIT)
    assert not writing_action_allowed(AIUsePolicy.EDITING_ONLY, WritingAction.OUTLINE)


def test_submission_requires_all_three_conditions():
    for a in [False, True]:
        for b in [False, True]:
            for c in [False, True]:
                assert submission_allowed(student_approved=a, portal_permission_verified=b, packet_verified=c) == (a and b and c)
