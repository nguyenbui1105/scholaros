from dataclasses import replace
from datetime import date, timedelta

import pytest

from scholaros.eligibility import assess_eligibility, authority_check, normalize
from scholaros.models import ClaimRecord, Decision, Opportunity, Severity, Student

TODAY = date(2026, 11, 18)
URL = "https://example.edu/award"
STUDENT = Student("undergraduate", "F-1", {"cs"}, 3.8, "PCC")
CLAIM = ClaimRecord("F-1 eligible", URL, TODAY, "F-1 may apply", "sha256-test", "reviewer")
BASE = Opportunity(
    "test", "Synthetic only", URL,
    eligible_levels={"undergraduate"}, eligible_visas={"F-1"},
    eligible_majors={"cs"}, min_gpa=3.0, allowed_schools={"PCC"},
    deadline=TODAY + timedelta(days=10), verified_on=TODAY,
    international_claim=CLAIM,
)


def decision(student: Student = STUDENT, opportunity: Opportunity = BASE) -> Decision:
    return assess_eligibility(student, opportunity, today=TODAY).decision


def test_positive_and_same_day_inclusive() -> None:
    assert decision() is Decision.ELIGIBLE
    assert decision(opportunity=replace(BASE, deadline=TODAY)) is Decision.ELIGIBLE


@pytest.mark.parametrize("field", ["academic_level", "visa_status", "majors", "gpa", "school"])
def test_missing_student_fields_are_unknown(field: str) -> None:
    assert decision(student=replace(STUDENT, **{field: None})) is Decision.NEEDS_VERIFICATION


def test_explicit_mismatch_collects_unknowns() -> None:
    o = replace(BASE, eligible_visas={"US-citizen"}, verified_on=None,
                unknown_requirements=("unresolved residency",))
    result = assess_eligibility(STUDENT, o, today=TODAY)
    assert result.decision is Decision.INELIGIBLE
    assert {"mismatch", "source_missing", "rule_ambiguous"}.issubset(
        {r.code for r in result.reasons}
    )
    assert result.requires_human_review


def test_missing_evidence_blocks() -> None:
    assert decision(opportunity=replace(BASE, international_claim=None)) is Decision.NEEDS_VERIFICATION
    assert decision(opportunity=replace(BASE, verified_on=None)) is Decision.NEEDS_VERIFICATION


def test_empty_constraint_blocks() -> None:
    assert decision(opportunity=replace(BASE, eligible_levels=())) is Decision.NEEDS_VERIFICATION


def test_case_whitespace_unicode_normalization() -> None:
    o = replace(BASE, eligible_levels=[" UNDERGRADUATE "], eligible_visas=(" f-1 ",),
                eligible_majors=[" CS "], allowed_schools=(" pcc ",))
    assert decision(opportunity=o) is Decision.ELIGIBLE
    assert normalize(" ＣＳ  ") == "cs"


@pytest.mark.parametrize("url", [
    "http://example.edu/x", "https://me:pw@example.edu/x",
    "https://example.edu:444/x", "https://example.edu:abc/x",
    "https://example.edu:999999/x", "https://bad.example.com/x",
    "https://127.0.0.1/x", "not a url",
])
def test_untrusted_urls(url: str) -> None:
    assert not authority_check(url)
    assert decision(opportunity=replace(BASE, official_url=url)) is Decision.NEEDS_VERIFICATION


def test_stale_and_future_verification() -> None:
    for day in [TODAY - timedelta(days=91), TODAY + timedelta(days=1)]:
        assert decision(opportunity=replace(BASE, verified_on=day)) is Decision.NEEDS_VERIFICATION


def test_expired_deadline() -> None:
    assert decision(opportunity=replace(BASE, deadline=TODAY - timedelta(days=1))) is Decision.INELIGIBLE


def test_missing_required_claim_quote() -> None:
    assert decision(opportunity=replace(BASE, international_claim=replace(CLAIM, quote=""))) is Decision.NEEDS_VERIFICATION


def test_hard_failure_never_disappears_with_unknown() -> None:
    o = replace(BASE, deadline=TODAY - timedelta(days=1), min_gpa=4.0,
                unknown_requirements=("uncertain",))
    result = assess_eligibility(STUDENT, o, today=TODAY)
    assert len([r for r in result.reasons if r.severity is Severity.HARD_FAILURE]) >= 2


def test_negative_freshness_rejected() -> None:
    with pytest.raises(ValueError):
        assess_eligibility(STUDENT, BASE, today=TODAY, freshness_days=-1)
