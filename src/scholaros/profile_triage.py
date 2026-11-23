"""Conservative, source-version-bound screening for locally imported awards.

Human-entered rule reviews are NOT independent verification of institutional
terms. The result is preliminary screening, never an ELIGIBLE or submitted
application. The reviewed quote must exist verbatim and support its literal
field value, with exceptions in its sentence rejected.
"""

from __future__ import annotations

import re
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .eligibility import _has_negation, _quote_context, _token, authority_check
from .records import StudentProfile
from .source_intake import ImportedAward
from .workspace import load_private, save_private

Screen = Literal["potential_match", "potential_mismatch", "needs_verification"]
Check = Literal["preliminary_match", "potential_mismatch", "needs_verification"]
_MINIMUM_GPA = re.compile(
    r"\b(?:minimum\s+gpa|gpa\s+(?:of\s+)?(?:at\s+least|minimum\s+of))"
    r"\s*[:=]?\s*(\d(?:\.\d{1,2})?)\b",
    re.IGNORECASE,
)
_DEADLINE = re.compile(r"\bdeadline\s*:\s*(\d{4}-\d{2}-\d{2})\b", re.IGNORECASE)
_VISA = re.compile(r"(?<!\w)f[\s-]*1(?!\w)", re.IGNORECASE)


class ReviewedConstraint(BaseModel):
    """Local reviewer attestation, not proof of provider identity or permission."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    award_id: str = Field(min_length=1)
    source_url: str
    content_hash: str = Field(min_length=64, max_length=64)
    reviewer_id: str = Field(min_length=1)
    acknowledged_manual_review: bool = False
    min_gpa: float | None = Field(default=None, ge=0, le=4)
    gpa_quote: str | None = None
    accepted_visa: str | None = None
    visa_quote: str | None = None
    deadline: date | None = None
    deadline_quote: str | None = None
    timezone_verified: bool = False
    all_other_requirements_verified: bool = False

    @model_validator(mode="after")
    def require_review_and_quotes(self) -> ReviewedConstraint:
        if not self.acknowledged_manual_review:
            raise ValueError("Reviewer must acknowledge manual source review")
        if self.min_gpa is not None and not self.gpa_quote:
            raise ValueError("GPA quote required for stated minimum")
        if self.accepted_visa is not None and not self.visa_quote:
            raise ValueError("Visa quote required for positive visa rule")
        if self.deadline is not None and not self.deadline_quote:
            raise ValueError("Deadline quote required")
        return self


def _quote_context_verified(text: str, quote: str | None, field: str) -> str:
    if not quote or quote not in text:
        raise ValueError(f"Missing or nonverbatim {field} quote")
    context = _quote_context(text, quote)
    if context is None:
        raise ValueError(f"Missing or nonverbatim {field} quote")
    if _has_negation(context) or re.search(
        r"\b(?:not\s+open\s+to|not\s+available\s+to|does\s+not\s+accept)\b",
        context,
        re.IGNORECASE,
    ):
        raise ValueError(f"Ambiguous or negative {field} rule near quoted text")
    return context


def validate_review(award: ImportedAward, review: ReviewedConstraint) -> None:
    """Recheck the record even when Pydantic.model_copy bypassed validation."""
    ReviewedConstraint.model_validate(review.model_dump())
    if (
        review.award_id != award.id
        or review.source_url != award.source_url
        or review.content_hash != award.content_hash
        or sha256(award.source_text.encode("utf-8")).hexdigest() != award.content_hash
    ):
        raise ValueError("Award source URL/hash or version mismatch")
    if not authority_check(award.source_url):
        raise ValueError("Source host is not on the institutional-domain list")
    if review.min_gpa is not None:
        context = _quote_context_verified(award.source_text, review.gpa_quote, "GPA")
        values = [float(match.group(1)) for match in _MINIMUM_GPA.finditer(context)]
        if not any(abs(review.min_gpa - value) < 1e-9 for value in values):
            raise ValueError("GPA minimum is not directly supported by its quote")
    if review.accepted_visa is not None:
        if _token(review.accepted_visa, "visa_status") != "f1":
            raise ValueError("Only F-1 positive screening is currently supported")
        context = _quote_context_verified(award.source_text, review.visa_quote, "visa")
        if not _VISA.search(context) or not re.search(
            r"\b(?:may\s+apply|eligible|open\s+to)\b", context, re.IGNORECASE
        ):
            raise ValueError("Positive visa rule not supported by the quote")
    if review.deadline is not None:
        context = _quote_context_verified(award.source_text, review.deadline_quote, "deadline")
        dates: list[date] = []
        for match in _DEADLINE.finditer(context):
            try:
                dates.append(date.fromisoformat(match.group(1)))
            except ValueError:
                continue
        if review.deadline not in dates:
            raise ValueError("Deadline is not directly supported by its quote")


def compare_profile(
    student: StudentProfile,
    award: ImportedAward,
    review: ReviewedConstraint | None,
    *,
    today: date,
) -> dict[str, Any]:
    """Local shortlist helper. NEVER returns eligible or final ineligible."""
    if type(today) is not date:
        raise ValueError("Use the provider-local calendar date for preliminary deadlines")
    checks: dict[str, Check] = {
        "visa_status": "needs_verification",
        "gpa": "needs_verification",
        "deadline": "needs_verification",
    }
    pending = [
        "Provider identity and per-award citizenship/residency rules not independently verified",
        "School, academic level, major, and all other award conditions need review",
        "Current application cycle, provider-local cutoff time and time zone need verification",
        "Confirm allowed AI assistance, required documents and destination before applying",
    ]
    if review is not None:
        validate_review(award, review)
        if review.accepted_visa is not None and student.visa_status:
            checks["visa_status"] = (
                "preliminary_match"
                if _token(student.visa_status, "visa_status")
                == _token(review.accepted_visa, "visa_status")
                else "potential_mismatch"
            )
        if review.min_gpa is not None and student.gpa is not None:
            checks["gpa"] = (
                "preliminary_match" if student.gpa >= review.min_gpa else "potential_mismatch"
            )
        if review.deadline is not None:
            checks["deadline"] = (
                "potential_mismatch"
                if today > review.deadline
                else "preliminary_match"
                if review.timezone_verified
                else "needs_verification"
            )
        if not review.all_other_requirements_verified:
            pending.append("Other award requirements were not confirmed by the reviewer")
    if any(value == "potential_mismatch" for value in checks.values()):
        screening: Screen = "potential_mismatch"
    elif review is not None and all(value == "preliminary_match" for value in checks.values()):
        screening = "potential_match"
    elif review is not None and (
        checks["visa_status"] == "preliminary_match" and checks["gpa"] == "preliminary_match"
    ):
        screening = "potential_match"
    else:
        screening = "needs_verification"
    return {
        "award_id": award.id,
        "title": award.title,
        "source_url": award.source_url,
        "content_hash": award.content_hash,
        "screening": screening,
        "eligibility": "needs_verification",
        "submission_status": "NOT_SUBMITTED",
        "checks": checks,
        "reviewed_by": review.reviewer_id if review else None,
        "remaining_reviews": pending,
        "caution": "Applicant-entered quote review is not independent award verification",
    }


def load_reviews(path: Path) -> list[ReviewedConstraint]:
    if not path.is_file():
        return []
    stored = load_private(path).get("reviews", [])
    if not isinstance(stored, list):
        raise ValueError("Corrupt encrypted reviews registry")
    return [ReviewedConstraint.model_validate(item) for item in stored]


def save_review(path: Path, review: ReviewedConstraint) -> None:
    """Encrypt source-specific review; replace only this exact source revision."""
    review = ReviewedConstraint.model_validate(review.model_dump())
    old = load_reviews(path)
    existing = [
        item
        for item in old
        if not (item.award_id == review.award_id and item.content_hash == review.content_hash)
    ]
    existing.append(review)
    save_private(path, {"reviews": [item.model_dump(mode="json") for item in existing]})
