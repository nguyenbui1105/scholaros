"""Typed reference entities. Never treat unspecified student fields as negative evidence."""
from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class Decision(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNKNOWN = "unknown"
    NEEDS_VERIFICATION = "needs_verification"


class Severity(StrEnum):
    HARD_FAILURE = "hard_failure"
    UNKNOWN = "unknown"
    INFO = "info"


class AIUsePolicy(StrEnum):
    PROHIBITED = "prohibited"
    EDITING_ONLY = "editing_only"
    ASSISTANCE_ALLOWED = "assistance_allowed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ClaimRecord:
    """Traceable claim, not self-authenticating proof of provider permission."""

    claim: str
    source_url: str
    retrieved_at: date
    quote: str
    content_hash: str
    verifier: str


@dataclass(frozen=True)
class Reason:
    code: str
    field: str
    message: str
    severity: Severity


@dataclass(frozen=True)
class Student:
    academic_level: str | None = None
    visa_status: str | None = None
    majors: Collection[str] | None = None
    gpa: float | None = None
    school: str | None = None


@dataclass(frozen=True)
class Opportunity:
    id: str
    title: str
    official_url: str
    eligible_levels: Collection[str] = ()
    eligible_visas: Collection[str] = ()
    eligible_majors: Collection[str] = ()
    min_gpa: float | None = None
    allowed_schools: Collection[str] = ()
    deadline: date | None = None
    verified_on: date | None = None
    ai_use_policy: AIUsePolicy = AIUsePolicy.UNKNOWN
    award_usd: int | None = None
    effort_hours: float | None = None
    unknown_requirements: tuple[str, ...] = ()
    international_claim: ClaimRecord | None = None
    source_text: str | None = None
    rule_claims: Mapping[str, ClaimRecord] = field(default_factory=dict)


@dataclass(frozen=True)
class EligibilityResult:
    decision: Decision
    reasons: tuple[Reason, ...]
    requires_human_review: bool = False


@dataclass(frozen=True)
class RankedOpportunity:
    opportunity: Opportunity
    score: float
    reasons: tuple[str, ...] = field(default_factory=tuple)
