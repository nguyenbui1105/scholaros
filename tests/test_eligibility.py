from dataclasses import replace
from datetime import date, timedelta

from scholaros.eligibility import assess_eligibility
from scholaros.models import Decision, Opportunity, Student

TODAY = date(2026, 11, 18)
STUDENT = Student("undergraduate", "F-1", frozenset({"cs"}), 3.8, "PCC")
BASE = Opportunity(
    "test", "Synthetic only", "https://example.org/award",
    eligible_levels=frozenset({"undergraduate"}), eligible_visas=frozenset({"F-1"}),
    eligible_majors=frozenset({"cs"}), min_gpa=3.0, allowed_schools=frozenset({"PCC"}),
    deadline=TODAY + timedelta(days=10), verified_on=TODAY,
    international_eligibility_confirmed=True,
)


def test_verified_positive():
    assert assess_eligibility(STUDENT, BASE, today=TODAY).decision is Decision.ELIGIBLE


def test_visa_mismatch_is_ineligible_even_when_other_fields_unknown():
    o = replace(BASE, eligible_visas=frozenset({"US-citizen"}), verified_on=None)
    assert assess_eligibility(STUDENT, o, today=TODAY).decision is Decision.INELIGIBLE


def test_unconfirmed_international_not_eligible():
    o = replace(BASE, international_eligibility_confirmed=False)
    assert assess_eligibility(STUDENT, o, today=TODAY).decision is Decision.NEEDS_VERIFICATION


def test_stale_source_requires_review():
    o = replace(BASE, verified_on=TODAY - timedelta(days=91))
    assert assess_eligibility(STUDENT, o, today=TODAY).requires_human_review


def test_missing_student_gpa_requires_review():
    s = replace(STUDENT, gpa=None)
    assert assess_eligibility(s, BASE, today=TODAY).decision is Decision.NEEDS_VERIFICATION


def test_expired_deadline_is_ineligible():
    assert assess_eligibility(STUDENT, replace(BASE, deadline=TODAY - timedelta(days=1)), today=TODAY).decision is Decision.INELIGIBLE


def test_future_verification_requires_review():
    o = replace(BASE, verified_on=TODAY + timedelta(days=1))
    assert assess_eligibility(STUDENT, o, today=TODAY).decision is Decision.NEEDS_VERIFICATION


def test_invalid_official_url_requires_review():
    o = replace(BASE, official_url="http://example.org/award")
    assert assess_eligibility(STUDENT, o, today=TODAY).decision is Decision.NEEDS_VERIFICATION


def test_school_mismatch_is_ineligible():
    o = replace(BASE, allowed_schools=frozenset({"Other College"}))
    assert assess_eligibility(STUDENT, o, today=TODAY).decision is Decision.INELIGIBLE


def test_explicit_unknown_requirements():
    o = replace(BASE, unknown_requirements=("citizenship clause not resolved",))
    assert assess_eligibility(STUDENT, o, today=TODAY).decision is Decision.NEEDS_VERIFICATION
