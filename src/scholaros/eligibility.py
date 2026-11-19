"""Fail-closed eligibility checks with structured, comprehensive explanations."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Collection
from datetime import date
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

from .models import (
    ClaimRecord,
    Decision,
    EligibilityResult,
    Opportunity,
    Reason,
    Severity,
    Student,
)


def normalize(value: str) -> str:
    """Casefold, normalize Unicode, and collapse whitespace."""
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _items(values: Collection[str] | None) -> frozenset[str]:
    return frozenset(normalize(v) for v in values or () if normalize(v))


def allowed_hosts(config: Path | None = None) -> frozenset[str]:
    """Read a limited domains YAML list without arbitrary YAML deserialization."""
    if config is None:
        config = Path(__file__).resolve().parents[2] / "config" / "official_domains.yaml"
    if not config.is_file():
        return frozenset({"edu", "gov"})
    hosts: set[str] = set()
    for raw in config.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("- "):
            host = line[2:].strip().lower().strip('"').strip("'")
            if host and all(c.isalnum() or c in ".-" for c in host):
                hosts.add(host.lstrip("."))
    return frozenset(hosts)


def authority_check(url: str, *, allowlist: Collection[str] | None = None) -> bool:
    """Conservative URL-shape/domain screen; not independent source verification."""
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            return False
        if parsed.port not in (None, 443) or parsed.fragment:
            return False
        host = parsed.hostname.lower().rstrip(".")
        if not host or host.replace(".", "").isdigit():
            return False
        allowed = allowlist if allowlist is not None else allowed_hosts()
        return any(host == domain or host.endswith("." + domain) for domain in allowed if domain)
    except (ValueError, TypeError, AttributeError):
        return False


def _claim_valid(
    claim: ClaimRecord | None,
    opportunity: Opportunity,
    today: date,
    freshness_days: int,
    allowlist: Collection[str] | None,
) -> bool:
    if claim is None:
        return False
    text = opportunity.source_text
    if text is None:
        return False
    return (
        sha256(text.encode("utf-8")).hexdigest() == claim.content_hash
        and claim.quote in text
        and ("f-1" in normalize(claim.quote) or "international students" in normalize(claim.quote))
        and normalize(claim.claim) in {"f-1 eligible", "international students eligible"}
        and bool(claim.quote.strip())
        and bool(claim.content_hash.strip())
        and bool(claim.verifier.strip())
        and claim.retrieved_at <= today
        and (today - claim.retrieved_at).days <= freshness_days
        and claim.source_url == opportunity.official_url
        and authority_check(claim.source_url, allowlist=allowlist)
    )


def _quote_supports(field: str, opportunity: Opportunity, quote: str) -> bool:
    """A sourced quote must actually name the encoded constraint, not merely exist."""
    if field == "deadline":
        return opportunity.deadline is not None and opportunity.deadline.isoformat() in quote
    if field == "gpa":
        return opportunity.min_gpa is not None and any(
            abs(float(v) - opportunity.min_gpa) < 1e-9 for v in re.findall(r"\d+(?:\.\d+)?", quote)
        )
    choices = {
        "academic_level": opportunity.eligible_levels,
        "visa_status": opportunity.eligible_visas,
        "school": opportunity.allowed_schools,
        "majors": opportunity.eligible_majors,
    }.get(field, ())
    normalized_quote = normalize(quote)
    return bool(choices) and all(
        re.search(r"(?<!\w)" + re.escape(choice) + r"(?!\w)", normalized_quote)
        for choice in _items(choices)
    )


def _rule_verified(
    field: str,
    opportunity: Opportunity,
    today: date,
    freshness_days: int,
    allowlist: Collection[str] | None,
) -> bool:
    claim = opportunity.rule_claims.get(field)
    text = opportunity.source_text
    if claim is None or text is None:
        return False
    return (
        claim.source_url == opportunity.official_url
        and authority_check(claim.source_url, allowlist=allowlist)
        and bool(claim.verifier.strip())
        and bool(claim.quote.strip())
        and claim.quote in text
        and _quote_supports(field, opportunity, claim.quote)
        and claim.content_hash == sha256(text.encode("utf-8")).hexdigest()
        and claim.retrieved_at <= today
        and (today - claim.retrieved_at).days <= freshness_days
    )


def assess_eligibility(
    student: Student,
    opportunity: Opportunity,
    *,
    today: date,
    freshness_days: int = 90,
    allowlist: Collection[str] | None = None,
) -> EligibilityResult:
    """Same-day deadlines are inclusive; freshness expires when age > freshness_days."""
    if freshness_days < 0:
        raise ValueError("freshness_days must be nonnegative")
    reasons: list[Reason] = []

    def add(code: str, field: str, message: str, severity: Severity) -> None:
        reasons.append(Reason(code, field, message, severity))

    # Missing values are unknown, never negative evidence.
    for key, value in (
        ("academic_level", student.academic_level),
        ("visa_status", student.visa_status),
        ("school", student.school),
        ("gpa", student.gpa),
        ("majors", student.majors),
    ):
        if (
            value is None
            or (isinstance(value, str) and not value.strip())
            or (key == "majors" and not _items(student.majors))
        ):
            add("student_missing", key, f"Student {key} is missing", Severity.UNKNOWN)

    comparisons: tuple[tuple[str, str | None, Collection[str]], ...] = (
        ("academic_level", student.academic_level, opportunity.eligible_levels),
        ("visa_status", student.visa_status, opportunity.eligible_visas),
        ("school", student.school, opportunity.allowed_schools),
    )
    for key, actual, allowed in comparisons:
        choices = _items(allowed)
        if not choices:
            add(
                "rule_unverified",
                key,
                f"No explicit {key} restriction was verified",
                Severity.UNKNOWN,
            )
        elif not _rule_verified(key, opportunity, today, freshness_days, allowlist):
            add(
                "rule_provenance_missing",
                key,
                "Rule has no snapshot-backed quote",
                Severity.UNKNOWN,
            )
        elif actual and normalize(actual) not in choices:
            add(
                "mismatch",
                key,
                f"Student {key} does not match verified constraint",
                Severity.HARD_FAILURE,
            )
    majors = _items(opportunity.eligible_majors)
    if not majors:
        add("rule_unverified", "majors", "Major restriction is not verified", Severity.UNKNOWN)
    elif not _rule_verified("majors", opportunity, today, freshness_days, allowlist):
        add("rule_provenance_missing", "majors", "Major rule lacks quote", Severity.UNKNOWN)
    elif (
        student.majors is not None
        and _items(student.majors)
        and not majors.intersection(_items(student.majors))
    ):
        add("mismatch", "majors", "Student majors do not match", Severity.HARD_FAILURE)
    if opportunity.min_gpa is None:
        add("rule_unverified", "gpa", "Minimum GPA rule is not verified", Severity.UNKNOWN)
    elif not _rule_verified("gpa", opportunity, today, freshness_days, allowlist):
        add("rule_provenance_missing", "gpa", "GPA rule lacks quote", Severity.UNKNOWN)
    elif student.gpa is not None and student.gpa < opportunity.min_gpa:
        add("mismatch", "gpa", "Student GPA is below minimum", Severity.HARD_FAILURE)

    if opportunity.deadline is None:
        add("deadline_missing", "deadline", "No verified deadline", Severity.UNKNOWN)
    elif not _rule_verified("deadline", opportunity, today, freshness_days, allowlist):
        add("rule_provenance_missing", "deadline", "Deadline lacks quote", Severity.UNKNOWN)
    elif opportunity.deadline < today:
        add("deadline_expired", "deadline", "Deadline has passed", Severity.HARD_FAILURE)

    if not authority_check(opportunity.official_url, allowlist=allowlist):
        add("source_untrusted", "official_url", "Official domain not recognized", Severity.UNKNOWN)
    if opportunity.verified_on is None:
        add("source_missing", "verified_on", "Verification timestamp absent", Severity.UNKNOWN)
    elif opportunity.verified_on > today or (today - opportunity.verified_on).days > freshness_days:
        add("source_stale", "verified_on", "Source is stale or future-dated", Severity.UNKNOWN)
    if not _claim_valid(
        opportunity.international_claim, opportunity, today, freshness_days, allowlist
    ):
        add(
            "claim_unverified",
            "international_claim",
            "International/F-1 eligibility lacks fresh traceable claim",
            Severity.UNKNOWN,
        )
    for requirement in opportunity.unknown_requirements:
        add("rule_ambiguous", "requirements", requirement, Severity.UNKNOWN)

    hard = any(r.severity is Severity.HARD_FAILURE for r in reasons)
    unknown = any(r.severity is Severity.UNKNOWN for r in reasons)
    if hard:
        decision = Decision.INELIGIBLE
    elif unknown:
        decision = Decision.NEEDS_VERIFICATION
    else:
        decision = Decision.ELIGIBLE
        add("all_checked", "eligibility", "All modeled gates verified", Severity.INFO)
    return EligibilityResult(decision, tuple(reasons), unknown)
