from dataclasses import replace
from datetime import date, timedelta
from hashlib import sha256

import pytest
from hypothesis import given
from hypothesis import strategies as st

from scholaros.eligibility import assess_eligibility, authority_check, normalize
from scholaros.models import ClaimRecord, Decision, Opportunity, Severity, Student

TODAY = date(2026, 11, 18)
URL = "https://example.edu/award"
STUDENT = Student("undergraduate", "F-1", {"cs"}, 3.8, "PCC")
SOURCE_TEXT = ("Undergraduate students are eligible. F-1 students are eligible. "
               "CS majors are eligible. PCC students are eligible. Minimum GPA 3.0. "
               "Deadline: 2026-11-28.")
HASH = sha256(SOURCE_TEXT.encode("utf-8")).hexdigest()
QUOTES = {
    "academic_level": "Undergraduate students are eligible",
    "visa_status": "F-1 students are eligible",
    "majors": "CS majors are eligible",
    "school": "PCC students are eligible",
    "gpa": "Minimum GPA 3.0",
    "deadline": "Deadline: 2026-11-28",
}
RULE_CLAIMS = {k: ClaimRecord(k, URL, TODAY, v, HASH, "reviewer")
               for k, v in QUOTES.items()}
CLAIM = ClaimRecord("F-1 eligible", URL, TODAY, QUOTES["visa_status"], HASH, "reviewer")
BASE = Opportunity(
    "test", "Synthetic only", URL,
    eligible_levels={"undergraduate"}, eligible_visas={"F-1"},
    eligible_majors={"cs"}, min_gpa=3.0, allowed_schools={"PCC"},
    deadline=TODAY + timedelta(days=10), verified_on=TODAY,
    international_claim=CLAIM, source_text=SOURCE_TEXT, rule_claims=RULE_CLAIMS,
)



def verified_adjust(
    *, deadline: date | None = None, gpa: float | None = None,
    visa: str | None = None,
) -> Opportunity:
    text = SOURCE_TEXT
    quotes = dict(QUOTES)
    new_deadline = deadline or BASE.deadline
    new_gpa = gpa if gpa is not None else BASE.min_gpa
    new_visa = BASE.eligible_visas
    if deadline is not None:
        quotes["deadline"] = f"Deadline: {deadline.isoformat()}"
        text = text.replace(QUOTES["deadline"], quotes["deadline"])
    if gpa is not None:
        quotes["gpa"] = f"Minimum GPA {gpa:.1f}"
        text = text.replace(QUOTES["gpa"], quotes["gpa"])
    if visa is not None:
        quotes["visa_status"] = f"Visa restriction: {visa}"
        text += " " + quotes["visa_status"]
        new_visa = {visa}
    digest = sha256(text.encode("utf-8")).hexdigest()
    claims = {
        key: replace(RULE_CLAIMS[key], quote=quote, content_hash=digest)
        for key, quote in quotes.items()
    }
    return replace(BASE, deadline=new_deadline, min_gpa=new_gpa,
                   eligible_visas=new_visa, source_text=text, rule_claims=claims,
                   international_claim=replace(CLAIM, content_hash=digest))


def decision(student: Student = STUDENT, opportunity: Opportunity = BASE) -> Decision:
    return assess_eligibility(student, opportunity, today=TODAY).decision


def test_positive_and_same_day_inclusive() -> None:
    assert decision() is Decision.ELIGIBLE
    assert decision(opportunity=verified_adjust(deadline=TODAY)) is Decision.ELIGIBLE


@pytest.mark.parametrize("field", ["academic_level", "visa_status", "majors", "gpa", "school"])
def test_missing_student_fields_are_unknown(field: str) -> None:
    assert decision(student=replace(STUDENT, **{field: None})) is Decision.NEEDS_VERIFICATION


def test_explicit_mismatch_collects_unknowns() -> None:
    o = replace(verified_adjust(visa="US-citizen"), verified_on=None,
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
    assert decision(opportunity=verified_adjust(deadline=TODAY - timedelta(days=1))) is Decision.INELIGIBLE


def test_missing_required_claim_quote() -> None:
    assert decision(opportunity=replace(BASE, international_claim=replace(CLAIM, quote=""))) is Decision.NEEDS_VERIFICATION


def test_hard_failure_never_disappears_with_unknown() -> None:
    o = replace(verified_adjust(deadline=TODAY - timedelta(days=1), gpa=4.0),
                unknown_requirements=("uncertain",))
    result = assess_eligibility(STUDENT, o, today=TODAY)
    assert len([r for r in result.reasons if r.severity is Severity.HARD_FAILURE]) >= 2


def test_negative_freshness_rejected() -> None:
    with pytest.raises(ValueError):
        assess_eligibility(STUDENT, BASE, today=TODAY, freshness_days=-1)

def test_missing_rule_provenance_is_not_eligible() -> None:
    assert decision(opportunity=replace(BASE, rule_claims={})) is Decision.NEEDS_VERIFICATION


def test_wrong_source_hash_or_quote_is_not_eligible() -> None:
    assert decision(opportunity=replace(BASE, source_text="Tampered")) is Decision.NEEDS_VERIFICATION


def test_unrelated_quote_cannot_verify_rule_value() -> None:
    assert decision(opportunity=replace(BASE, eligible_visas={"J-1"})) is Decision.NEEDS_VERIFICATION
    assert decision(opportunity=replace(BASE, deadline=TODAY)) is Decision.NEEDS_VERIFICATION


@given(field=st.sampled_from(["academic_level", "visa_status", "majors", "gpa", "school"]))
def test_property_missing_student_value_never_eligible(field: str) -> None:
    assert decision(student=replace(STUDENT, **{field: None})) is not Decision.ELIGIBLE
