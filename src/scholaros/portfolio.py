"""Deterministic effort-budget optimizer for already eligible ranked opportunities."""
from __future__ import annotations

from .models import RankedOpportunity


def optimize_portfolio(
    ranked: list[RankedOpportunity], hours_budget: float, *, hour_step: float = 0.5
) -> list[RankedOpportunity]:
    """0/1 knapsack using priority points, not expected awards or success probabilities."""
    if hours_budget < 0 or hour_step <= 0:
        raise ValueError("hours_budget must be >=0 and hour_step positive")
    capacity = int(hours_budget / hour_step)
    # Missing effort is not zero effort and is therefore skipped.
    slots: dict[int, tuple[float, tuple[int, ...]]] = {0: (0.0, ())}
    for index, item in enumerate(ranked):
        effort = item.opportunity.effort_hours
        if effort is None or effort <= 0:
            continue
        units = int(-(-effort // hour_step))  # round up so budget is never exceeded
        if units > capacity:
            continue
        for used, (total, selected) in sorted(list(slots.items()), reverse=True):
            next_used = used + units
            if next_used > capacity:
                continue
            proposal = total + item.score
            previous = slots.get(next_used)
            if previous is None or proposal > previous[0]:
                slots[next_used] = (proposal, (*selected, index))
    _, chosen = max(slots.values(), key=lambda entry: (entry[0], -len(entry[1])))
    return [ranked[i] for i in chosen]
