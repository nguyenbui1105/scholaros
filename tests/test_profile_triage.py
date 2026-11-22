"""Offline regression contracts for evidence-linked, conservative applicant triage."""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from scholaros.profile_triage import (
    ReviewedConstraint,
    compare_profile,
    load_reviews,
    save_review,
)
from scholaros.records import StudentProfile
from scholaros.source_intake import parse_award

SOURCE = (
    "The award is open to F-1 international students. "
    "Minimum GPA 3.5 is required. "
    "Deadline: 2027-05-01. "
    "Applicants must meet additional citizenship or residency requirements."
)
URL = "https://scholarships.example.edu/award/2027"


def award() -> object:
    return parse_award(
        title="Example Individual Scholarship",
        source_url=URL,
        source_text=SOURCE,
        imported_at=datetime(2026, 11, 22, tzinfo=UTC),
    )


def profile(gpa: float | None = 3.8, visa: str | None = "F-1") -> StudentProfile:
    return StudentProfile(
        student_id="local-student",
        gpa=gpa,
        visa_status=visa,
        school="Example College",
        academic_level="undergraduate",
        majors=("computer science",),
        consent_to_store=True,
    )


def reviewed(*, gpa: float = 3.5) -> ReviewedConstraint:
    case = award()
    return ReviewedConstraint(
        award_id=case.id,
        source_url=URL,
        content_hash=case.content_hash,
        reviewer_id="applicant-local",
        acknowledged_manual_review=True,
        min_gpa=gpa,
        gpa_quote="Minimum GPA 3.5",
        accepted_visa="F-1",
        visa_quote="F-1 international students",
        deadline=date(2027, 5, 1),
        deadline_quote="Deadline: 2027-05-01",
        timezone_verified=False,
        all_other_requirements_verified=False,
    )


def test_reviewed_quotes_provide_preliminary_gates_only() -> None:
    from scholaros.source_intake import ImportedAward

    case = award()
    assert isinstance(case, ImportedAward)
    result = compare_profile(profile(), case, reviewed(), today=date(2026, 11, 22))
    assert result["screening"] == "potential_match"
    assert result["eligibility"] == "needs_verification"
    assert result["submission_status"] == "NOT_SUBMITTED"
    assert result["checks"]["gpa"] == "preliminary_match"
    assert result["checks"]["visa_status"] == "preliminary_match"
    assert result["checks"]["deadline"] == "needs_verification"
    assert any("citizenship" in item.lower() for item in result["remaining_reviews"])


def test_gpa_mismatch_is_not_claimed_official_ineligibility() -> None:
    result = compare_profile(profile(gpa=3.0), award(), reviewed(), today=date(2026, 11, 22))
    assert result["screening"] == "potential_mismatch"
    assert result["checks"]["gpa"] == "potential_mismatch"
    assert result["eligibility"] == "needs_verification"


def test_missing_student_info_remains_unknown() -> None:
    result = compare_profile(
        profile(gpa=None, visa=None), award(), reviewed(), today=date(2026, 11, 22)
    )
    assert result["screening"] == "needs_verification"
    assert result["checks"]["visa_status"] == "needs_verification"
    assert result["checks"]["gpa"] == "needs_verification"


def test_unreviewed_pages_never_become_eligible() -> None:
    result = compare_profile(profile(), award(), None, today=date(2026, 11, 22))
    assert result["screening"] == "needs_verification"
    assert result["eligibility"] == "needs_verification"
    assert result["checks"]["visa_status"] == "needs_verification"


def test_missing_quote_rejected() -> None:
    with pytest.raises(ValueError, match="quote"):
        compare_profile(
            profile(),
            award(),
            reviewed().model_copy(update={"visa_quote": "Missing quote"}),
            today=date(2026, 11, 22),
        )


def test_tampered_source_hash_rejected() -> None:
    with pytest.raises(ValueError, match="hash"):
        compare_profile(
            profile(),
            award(),
            reviewed().model_copy(update={"content_hash": "0" * 64}),
            today=date(2026, 11, 22),
        )


def test_gpa_value_not_proved_by_quote_rejected() -> None:
    with pytest.raises(ValueError, match="GPA"):
        compare_profile(profile(), award(), reviewed(gpa=4.0), today=date(2026, 11, 22))


def test_negated_visa_quote_cannot_be_positive() -> None:
    source = SOURCE.replace(
        "open to F-1 international students", "not open to F-1 international students"
    )
    case = parse_award(title="Different award", source_url=URL, source_text=source)
    review = reviewed().model_copy(update={"award_id": case.id, "content_hash": case.content_hash})
    with pytest.raises(ValueError, match="negative"):
        compare_profile(profile(), case, review, today=date(2026, 11, 22))


def test_source_edit_invalidates_review() -> None:
    modified = parse_award(title="Updated award", source_url=URL, source_text=SOURCE + " Update.")
    with pytest.raises(ValueError, match="hash"):
        compare_profile(profile(), modified, reviewed(), today=date(2026, 11, 22))


def test_deadline_in_past_is_a_potential_mismatch_only() -> None:
    result = compare_profile(profile(), award(), reviewed(), today=date(2027, 5, 2))
    assert result["checks"]["deadline"] == "potential_mismatch"
    assert result["eligibility"] == "needs_verification"


def test_missing_reviewer_acknowledgment_fails_closed() -> None:
    with pytest.raises(ValueError, match="acknowledg"):
        compare_profile(
            profile(),
            award(),
            reviewed().model_copy(update={"acknowledged_manual_review": False}),
            today=date(2026, 11, 22),
        )


def test_encrypted_review_store_and_revision_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SCHOLAROS_FERNET_KEY", Fernet.generate_key().decode())
    path = tmp_path / "reviews.enc"
    first = reviewed()
    save_review(path, first)
    assert load_reviews(path)[0].award_id == first.award_id
    assert first.content_hash not in path.read_bytes().decode()
    new = first.model_copy(update={"reviewer_id": "revised-local-reviewer"})
    save_review(path, new)
    assert len(load_reviews(path)) == 1
    assert load_reviews(path)[0].reviewer_id == "revised-local-reviewer"
