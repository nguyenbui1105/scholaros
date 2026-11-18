"""Typed, deliberately small reference-domain models."""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class Decision(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNKNOWN = "unknown"
    NEEDS_VERIFICATION = "needs_verification"


class AIUsePolicy(str, Enum):
    PROHIBITED = "prohibited"
    EDITING_ONLY = "editing_only"
    ASSISTANCE_ALLOWED = "assistance_allowed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Student:
    """Only non-sensitive attributes needed for the offline demo."""

    academic_level: str
    visa_status: str
    majors: frozenset[str]
    gpa: float | None = None
    school: str | None = None


@dataclass(frozen=True)
class Opportunity:
    id: str
    title: str
    official_url: str
    eligible_levels: frozenset[str] = frozenset()
    eligible_visas: frozenset[str] = frozenset()
    eligible_majors: frozenset[str] = frozenset()
    min_gpa: float | None = None
    allowed_schools: frozenset[str] = frozenset()
    deadline: date | None = None
    verified_on: date | None = None
    ai_use_policy: AIUsePolicy = AIUsePolicy.UNKNOWN
    award_usd: int | None = None
    effort_hours: float | None = None
    unknown_requirements: tuple[str, ...] = ()
    # True only if an authoritative source has explicitly confirmed international eligibility.
    international_eligibility_confirmed: bool = False


@dataclass(frozen=True)
class EligibilityResult:
    decision: Decision
    reasons: tuple[str, ...]
    requires_human_review: bool = False


@dataclass(frozen=True)
class RankedOpportunity:
    opportunity: Opportunity
    score: float
    reasons: tuple[str, ...] = field(default_factory=tuple)
