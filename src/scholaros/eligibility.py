"""Conservative, deterministic eligibility checks; never infer unknown terms."""
from datetime import date
from urllib.parse import urlparse

from .models import Decision, EligibilityResult, Opportunity, Student


def _official_https(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.hostname)


def assess_eligibility(
    student: Student, opportunity: Opportunity, *, today: date, freshness_days: int = 90
) -> EligibilityResult:
    """A negative known constraint dominates; uncertainty blocks positive conclusions."""
    if freshness_days < 0:
        raise ValueError("freshness_days must be nonnegative")
    reasons: list[str] = []
    failures: list[str] = []
    unknowns: list[str] = []

    if opportunity.deadline is not None and opportunity.deadline < today:
        failures.append("deadline has passed")
    if opportunity.eligible_levels and student.academic_level not in opportunity.eligible_levels:
        failures.append("academic level is not eligible")
    if opportunity.eligible_visas and student.visa_status not in opportunity.eligible_visas:
        failures.append("visa status is not eligible")
    if opportunity.eligible_majors and not student.majors.intersection(opportunity.eligible_majors):
        failures.append("major is not eligible")
    if opportunity.allowed_schools:
        if student.school is None:
            unknowns.append("school is missing")
        elif student.school not in opportunity.allowed_schools:
            failures.append("school is not eligible")
    if opportunity.min_gpa is not None:
        if student.gpa is None:
            unknowns.append("GPA is missing")
        elif student.gpa < opportunity.min_gpa:
            failures.append("GPA is below minimum")

    if failures:
        return EligibilityResult(Decision.INELIGIBLE, tuple(failures))
    if not _official_https(opportunity.official_url):
        unknowns.append("official HTTPS source URL is missing or invalid")
    if opportunity.deadline is None:
        unknowns.append("deadline has not been verified")
    if opportunity.verified_on is None:
        unknowns.append("source verification date is missing")
    elif opportunity.verified_on > today:
        unknowns.append("verification timestamp is in the future")
    elif (today - opportunity.verified_on).days > freshness_days:
        unknowns.append("source verification is stale")
    if not opportunity.international_eligibility_confirmed:
        unknowns.append("international student eligibility unconfirmed")
    unknowns.extend(opportunity.unknown_requirements)

    if unknowns:
        return EligibilityResult(Decision.NEEDS_VERIFICATION, tuple(unknowns), True)
    reasons.append("all encoded eligibility gates passed with verified evidence")
    return EligibilityResult(Decision.ELIGIBLE, tuple(reasons))
