"""Explainable prioritization, not a prediction of award probability."""
from .models import Decision, EligibilityResult, Opportunity, RankedOpportunity, Student


def rank_eligible(
    student: Student,
    opportunities: list[tuple[Opportunity, EligibilityResult]],
    *,
    fit_weight: float = 0.5,
    value_weight: float = 0.3,
    ease_weight: float = 0.2,
) -> list[RankedOpportunity]:
    weights = (fit_weight, value_weight, ease_weight)
    if any(w < 0 for w in weights) or sum(weights) <= 0:
        raise ValueError("ranking weights must be nonnegative with a positive sum")
    total = sum(weights)
    ranked: list[RankedOpportunity] = []
    for o, result in opportunities:
        if result.decision is not Decision.ELIGIBLE:
            continue
        # Heuristics are only priority signals; not probabilities.
        fit = 100.0 if o.eligible_majors and student.majors.intersection(o.eligible_majors) else 65.0
        value = min(100.0, max(0.0, (o.award_usd or 0) / 100.0))
        ease = 50.0 if o.effort_hours is None else max(0.0, 100.0 - 10.0 * o.effort_hours)
        score = (fit * fit_weight + value * value_weight + ease * ease_weight) / total
        ranked.append(
            RankedOpportunity(
                o, round(score, 2),
                (f"fit={fit:.0f}", f"value={value:.0f}", f"ease={ease:.0f}",
                 "priority score is not an admission probability"),
            )
        )
    return sorted(ranked, key=lambda x: (-x.score, x.opportunity.id))
