"""Conservative eligibility evaluation with independently checkable source assertions."""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Collection
from datetime import date, datetime
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from .models import (
    ClaimRecord,
    Decision,
    EligibilityResult,
    Opportunity,
    Reason,
    Severity,
    Student,
)

_DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "official_domains.yaml"
_NEGATION = re.compile(
    r"\b(?:not\s+eligible|ineligible|not\s+permitted|cannot\s+apply|"
    r"may\s+not\s+apply|except|excluding|excluded|ineligible\s+for)\b",
    re.IGNORECASE,
)
_GPA_CONTEXT = re.compile(r"\b(?:gpa|grade\s+point\s+average)\b", re.IGNORECASE)
_DATE_TEXT = re.compile(
    r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)|"
    r"\b((?:january|february|march|april|may|june|july|august|september|october|"
    r"november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
    r"\.?\s+\d{1,2},?\s+\d{4})\b",
    re.IGNORECASE,
)


def normalize(value: str) -> str:
    """Unicode NFKC, Unicode casefold and whitespace normalization."""
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _token(value: str, field: str) -> str:
    clean = normalize(value)
    if field == "visa_status":
        compact = re.sub(r"[\s-]+", "", clean)
        if compact == "f1":
            return "f1"
        if compact == "j1":
            return "j1"
        return clean
    if field == "academic_level":
        compact = re.sub(r"[^a-z]", "", clean)
        if compact in {"undergraduate", "undergrad", "bachelor", "bachelors"}:
            return "undergraduate"
        if compact in {"graduate", "grad", "masters", "master"}:
            return "graduate"
        return clean
    return clean


def _items(values: Collection[str] | None, field: str = "") -> frozenset[str]:
    if values is None:
        return frozenset()
    if isinstance(values, (str, bytes)):
        raise TypeError("Constraints must be a collection of strings, not a bare string")
    if any(not isinstance(item, str) for item in values):
        raise TypeError("Every constraint must be a string")
    return frozenset(_token(item, field) for item in values if _token(item, field))


def _domain(value: str) -> str:
    raw = normalize(value).strip(".")
    if not raw or any(char in raw for char in "/:@*\\\t\n "):
        raise ValueError(f"Invalid allowlist domain: {value!r}")
    try:
        result = raw.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError(f"Invalid IDNA domain: {value!r}") from exc
    if not all(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", part) for part in result.split(".")
    ):
        raise ValueError(f"Invalid domain labels: {value!r}")
    return result


@lru_cache(maxsize=32)
def _read_allowlist(path: str, mtime_ns: int, size: int) -> frozenset[str]:
    """Safely parse real YAML; stat keys invalidate the cache after edits."""
    del mtime_ns, size
    with Path(path).open(encoding="utf-8") as handle:
        try:
            document = yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            raise ValueError("Malformed official domain YAML") from exc
    if not isinstance(document, dict) or not isinstance(document.get("domains"), list):
        raise ValueError("Official domain YAML must contain a domains list")
    values = document["domains"]
    if not values or any(not isinstance(value, str) for value in values):
        raise ValueError("Official domain allowlist must contain nonempty strings")
    return frozenset(_domain(value) for value in values)


def allowed_hosts(config: Path | None = None) -> frozenset[str]:
    """Missing, malformed and empty allowlists are configuration errors, not fallbacks."""
    target = (config if config is not None else _DEFAULT_CONFIG).resolve()
    stat = target.stat()  # Deliberately raises FileNotFoundError.
    return _read_allowlist(str(target), stat.st_mtime_ns, stat.st_size)


def authority_check(url: str, *, allowlist: Collection[str] | None = None) -> bool:
    """URL/domain plausibility only; never substitutes for verifying provider identity."""
    permitted = (
        frozenset(_domain(item) for item in _items(allowlist))
        if allowlist is not None
        else allowed_hosts()
    )
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
            or parsed.port not in (None, 443)
        ):
            return False
        host = _domain(parsed.hostname)
        # A bare suffix such as https://gov/ is not a usable official host.
        if "." not in host or host.replace(".", "").isdigit():
            return False
        return any(host == domain or host.endswith("." + domain) for domain in permitted)
    except (ValueError, TypeError, AttributeError):
        return False


def _valid_gpa(value: object) -> bool:
    """Only the documented US 0-4 scale is currently supported."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and 0.0 <= value <= 4.0
    )


def _dated_values(text: str) -> frozenset[date]:
    extracted: set[date] = set()
    for match in _DATE_TEXT.finditer(text):
        candidate = match.group(1) or match.group(2)
        if candidate is None:
            continue
        if match.group(1):
            try:
                extracted.add(date.fromisoformat(candidate))
            except ValueError:
                continue
        else:
            normalized = candidate.replace(".", "")
            for pattern in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
                try:
                    extracted.add(datetime.strptime(normalized, pattern).date())
                    break
                except ValueError:
                    continue
    return frozenset(extracted)


def _quote_context(source: str, quote: str) -> str | None:
    """Find the containing sentence; avoid accepting a clipped positive quote with an exception."""
    start = source.find(quote)
    if start < 0:
        return None
    # Split only at punctuation followed by whitespace, not decimal points.
    left = list(re.finditer(r"[.!?;](?=\s|$)|\n", source[:start]))
    begin = left[-1].end() if left else 0
    right = re.search(r"[.!?;](?=\s|$)|\n", source[start + len(quote) :])
    end = start + len(quote) + right.start() if right else len(source)
    return source[begin:end]


def _has_negation(text: str) -> bool:
    return _NEGATION.search(normalize(text)) is not None


def _contains_token(quote: str, target: str, field: str) -> bool:
    normalized = normalize(quote)
    item = _token(target, field)
    if field == "visa_status" and item in {"f1", "j1"}:
        return (
            re.search(r"(?<!\w)" + item[0] + r"[\s-]*" + item[1:] + r"(?!\w)", normalized)
            is not None
        )
    if field == "academic_level" and item == "undergraduate":
        return re.search(r"\b(?:undergraduate|undergrad|bachelor'?s?)\b", normalized) is not None
    if field == "academic_level" and item == "graduate":
        return re.search(r"\b(?:graduate|grad|master'?s?)\b", normalized) is not None
    return re.search(r"(?<!\w)" + re.escape(item) + r"(?!\w)", normalized) is not None


def _quote_supports(field: str, opportunity: Opportunity, quote: str) -> bool:
    if field == "international_claim":
        return (
            _contains_token(quote, "f1", "visa_status")
            or "international students" in normalize(quote)
        ) and bool(re.search(r"\b(?:eligible|may\s+apply|visa\s*:\s*f[\s-]*1)\b", normalize(quote)))
    if field == "deadline":
        return opportunity.deadline is not None and opportunity.deadline in _dated_values(quote)
    if field == "gpa":
        if opportunity.min_gpa is None or not _valid_gpa(opportunity.min_gpa):
            return False
        numeric = re.findall(
            r"\b(?:minimum\s+gpa|gpa|grade\s+point\s+average)"
            r"\s*(?:of|is|at\s+least)?\s*[:=]?\s*(\d+(?:\.\d+)?)",
            quote,
            flags=re.IGNORECASE,
        )
        return any(abs(float(value) - opportunity.min_gpa) < 1e-9 for value in numeric)
    choices: Collection[str] = {
        "academic_level": opportunity.eligible_levels,
        "visa_status": opportunity.eligible_visas,
        "school": opportunity.allowed_schools,
        "majors": opportunity.eligible_majors,
    }.get(field, ())
    return bool(_items(choices, field)) and all(
        _contains_token(quote, item, field) for item in choices
    )


def _verified_claim(
    field: str,
    claim: ClaimRecord | None,
    opportunity: Opportunity,
    today: date,
    freshness_days: int,
    allowlist: Collection[str] | None,
) -> bool:
    """Single provenance, quote-context, value, timestamp and domain verifier."""
    source = opportunity.source_text
    if claim is None or source is None or not claim.quote.strip() or not claim.verifier.strip():
        return False
    context = _quote_context(source, claim.quote)
    if context is None or _has_negation(context):
        return False
    return (
        claim.source_url == opportunity.official_url
        and authority_check(claim.source_url, allowlist=allowlist)
        and claim.content_hash == sha256(source.encode("utf-8")).hexdigest()
        and claim.retrieved_at <= today
        and (today - claim.retrieved_at).days <= freshness_days
        and _quote_supports(field, opportunity, claim.quote)
    )


def _claim_valid(
    claim: ClaimRecord | None,
    opportunity: Opportunity,
    today: date,
    freshness_days: int,
    allowlist: Collection[str] | None,
) -> bool:
    """Compatibility wrapper using the same logic as each requirement."""
    return _verified_claim(
        "international_claim", claim, opportunity, today, freshness_days, allowlist
    )


def _rule_verified(
    field: str,
    opportunity: Opportunity,
    today: date,
    freshness_days: int,
    allowlist: Collection[str] | None,
) -> bool:
    return _verified_claim(
        field,
        opportunity.rule_claims.get(field),
        opportunity,
        today,
        freshness_days,
        allowlist,
    )


def assess_eligibility(
    student: Student,
    opportunity: Opportunity,
    *,
    today: date,
    freshness_days: int = 90,
    allowlist: Collection[str] | None = None,
) -> EligibilityResult:
    """Explicit provider-local calendar date; same-day deadline inclusive.

    The caller must establish the scholarship provider's timezone/cutoff. No
    implicit wall-clock conversion is performed in this decision engine.
    """
    if type(today) is not date:
        raise TypeError("today must be an explicit provider-local datetime.date")
    if freshness_days < 0:
        raise ValueError("freshness_days must be nonnegative")
    reasons: list[Reason] = []

    def add(code: str, field: str, message: str, severity: Severity) -> None:
        reasons.append(Reason(code, field, message, severity))

    for key, value in (
        ("academic_level", student.academic_level),
        ("visa_status", student.visa_status),
        ("school", student.school),
        ("majors", student.majors),
    ):
        if (
            value is None
            or (isinstance(value, str) and not value.strip())
            or (key == "majors" and not _items(student.majors, "majors"))
        ):
            add("student_missing", key, f"Student {key} is missing", Severity.UNKNOWN)

    if not _valid_gpa(student.gpa):
        add("student_gpa_invalid", "gpa", "Missing or invalid GPA on 0-4 scale", Severity.UNKNOWN)
    if opportunity.min_gpa is not None and not _valid_gpa(opportunity.min_gpa):
        add(
            "rule_gpa_invalid",
            "gpa",
            "Unrecognized or invalid required GPA scale",
            Severity.UNKNOWN,
        )

    comparisons: tuple[tuple[str, str | None, Collection[str]], ...] = (
        ("academic_level", student.academic_level, opportunity.eligible_levels),
        ("visa_status", student.visa_status, opportunity.eligible_visas),
        ("school", student.school, opportunity.allowed_schools),
    )
    for field, actual, allowed in comparisons:
        values = _items(allowed, field)
        if not values:
            add("rule_unverified", field, f"No explicit {field} rule", Severity.UNKNOWN)
        elif not _rule_verified(field, opportunity, today, freshness_days, allowlist):
            add(
                "rule_provenance_missing",
                field,
                "Rule lacks valid supporting source quote",
                Severity.UNKNOWN,
            )
        elif actual and _token(actual, field) not in values:
            add("mismatch", field, f"Student {field} does not match rule", Severity.HARD_FAILURE)

    majors = _items(opportunity.eligible_majors, "majors")
    if not majors:
        add("rule_unverified", "majors", "Major restriction unverified", Severity.UNKNOWN)
    elif not _rule_verified("majors", opportunity, today, freshness_days, allowlist):
        add("rule_provenance_missing", "majors", "Major rule lacks valid quote", Severity.UNKNOWN)
    elif (
        student.majors is not None
        and _items(student.majors, "majors")
        and not (majors.intersection(_items(student.majors, "majors")))
    ):
        add("mismatch", "majors", "Student majors do not match", Severity.HARD_FAILURE)

    if opportunity.min_gpa is None:
        add("rule_unverified", "gpa", "Minimum GPA is unverified", Severity.UNKNOWN)
    elif not _valid_gpa(opportunity.min_gpa):
        pass  # Already accounted for as unknown.
    elif not _rule_verified("gpa", opportunity, today, freshness_days, allowlist):
        add("rule_provenance_missing", "gpa", "GPA rule lacks valid quote", Severity.UNKNOWN)
    elif (
        student.gpa is not None
        and opportunity.min_gpa is not None
        and _valid_gpa(student.gpa)
        and student.gpa < opportunity.min_gpa
    ):
        add("mismatch", "gpa", "Student GPA is below required minimum", Severity.HARD_FAILURE)

    if opportunity.deadline is None:
        add("deadline_missing", "deadline", "No verified deadline", Severity.UNKNOWN)
    elif not _rule_verified("deadline", opportunity, today, freshness_days, allowlist):
        add("rule_provenance_missing", "deadline", "Deadline lacks valid quote", Severity.UNKNOWN)
    elif opportunity.deadline < today:
        add("deadline_expired", "deadline", "Deadline has passed", Severity.HARD_FAILURE)

    if not authority_check(opportunity.official_url, allowlist=allowlist):
        add("source_untrusted", "official_url", "Host is not allowlisted", Severity.UNKNOWN)
    if opportunity.verified_on is None:
        add("source_missing", "verified_on", "Verification timestamp absent", Severity.UNKNOWN)
    elif opportunity.verified_on > today or (today - opportunity.verified_on).days > freshness_days:
        add("source_stale", "verified_on", "Source is stale or in the future", Severity.UNKNOWN)
    if not _claim_valid(
        opportunity.international_claim, opportunity, today, freshness_days, allowlist
    ):
        add(
            "claim_unverified",
            "international_claim",
            "International eligibility claim lacks supported positive quote",
            Severity.UNKNOWN,
        )
    for item in opportunity.unknown_requirements:
        add("rule_ambiguous", "requirements", item, Severity.UNKNOWN)

    hard = any(reason.severity is Severity.HARD_FAILURE for reason in reasons)
    unknown = any(reason.severity is Severity.UNKNOWN for reason in reasons)
    decision = (
        Decision.INELIGIBLE
        if hard
        else Decision.NEEDS_VERIFICATION
        if unknown
        else Decision.ELIGIBLE
    )
    if decision is Decision.ELIGIBLE:
        add("all_checked", "eligibility", "All modeled gates verified", Severity.INFO)
    return EligibilityResult(decision, tuple(reasons), unknown)
