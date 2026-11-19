"""Independently labeled synthetic benchmark; never evaluate real award outcomes."""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import replace
from datetime import date
from hashlib import sha256
from pathlib import Path

from .eligibility import assess_eligibility
from .models import ClaimRecord, Decision, Opportunity, Student
from .records import EvidenceItem
from .workflow import ROOT, build_synthetic
from .writing import review_claims

BENCHMARK_DATE = date(2026, 11, 18)
MIN_CASES = 60
MAX_FALSE_ELIGIBLE_RATE = 0.0
MIN_UNSUPPORTED_CLAIM_RECALL = 0.95


def _replace_source_quote(opportunity: Opportunity, field: str, value: str) -> Opportunity:
    if opportunity.source_text is None:
        raise ValueError("Missing benchmark source text")
    if field == "international":
        previous = opportunity.international_claim
    else:
        previous = opportunity.rule_claims[field]
    if previous is None or previous.quote not in opportunity.source_text:
        raise ValueError(f"Missing original quote for {field}")
    source = opportunity.source_text.replace(previous.quote, value, 1)
    digest = sha256(source.encode("utf-8")).hexdigest()
    claims = {
        key: replace(record, content_hash=digest,
                     quote=value if key == field else record.quote)
        for key, record in opportunity.rule_claims.items()
    }
    international = opportunity.international_claim
    if international is not None:
        international = replace(international, content_hash=digest,
                                quote=value if field == "international" else international.quote)
    return replace(opportunity, source_text=source, rule_claims=claims,
                   international_claim=international)


def _change_case(student: Student, award: Opportunity, field: str, value: str
                 ) -> tuple[Student, Opportunity]:
    if field == "academic_level":
        return replace(student, academic_level=None if value == "NONE" else value), award
    if field == "visa_status":
        return replace(student, visa_status=None if value == "NONE" else value), award
    if field == "majors":
        return replace(student, majors=None if value == "NONE" else (value,)), award
    if field == "school":
        return replace(student, school=None if value == "NONE" else value), award
    if field == "gpa":
        return replace(student, gpa=None if value == "NONE" else float(value)), award
    if field == "requirement_gpa":
        return student, replace(award, min_gpa=float(value))
    if field == "host":
        return student, replace(award, official_url=value)
    if field.startswith("quote:"):
        return student, _replace_source_quote(award, field.partition(":")[2], value)
    raise ValueError(f"Unknown benchmark field {field!r}")


def evaluate(path: Path | None = None) -> dict[str, float | int]:
    source = path or ROOT / "examples" / "benchmark_adversarial.csv"
    with source.open(newline="", encoding="utf-8") as handle:
        cases = list(csv.DictReader(handle))
    if len(cases) < MIN_CASES:
        raise ValueError(f"At least {MIN_CASES} independently labeled pairs are required")
    if len({row["case_id"] for row in cases}) != len(cases):
        raise ValueError("Duplicate benchmark case IDs")
    tp = fp = fn = tn = correct = 0
    for row in cases:
        student, award, _, _, _ = build_synthetic(today=BENCHMARK_DATE)
        modified, opportunity = _change_case(student, award, row["field"], row["value"])
        predicted = assess_eligibility(
            modified, opportunity, today=BENCHMARK_DATE
        ).decision
        gold = Decision(row["expected"])
        if predicted is gold:
            correct += 1
        if predicted is Decision.ELIGIBLE and gold is Decision.ELIGIBLE:
            tp += 1
        elif predicted is Decision.ELIGIBLE:
            fp += 1
        elif gold is Decision.ELIGIBLE:
            fn += 1
        else:
            tn += 1

    evidence = [EvidenceItem(
        id="supported", student_id="synthetic", confirmed_by_student=True,
        statement="I practiced programming every day.",
    )]
    unsupported = [
        f"I received fictional award number {i}." for i in range(10)
    ] + [
        "I interned at a university research lab.",
        "I graduated with perfect marks.",
        "I developed a published medical model.",
        "I led an international competition team.",
        "I earned a full scholarship.",
        "I completed 500 volunteer hours.",
        "I authored a journal paper.",
        "I founded a charitable organization.",
        "I won a statewide programming competition.",
        "I served as student body president.",
    ]
    detected = sum(
        bool(review_claims(sentence, evidence).unsupported) for sentence in unsupported
    )
    return {
        "pairs": len(cases),
        "exact_state_accuracy": round(correct / len(cases), 4),
        "eligible_precision": round(tp / (tp + fp), 4) if tp + fp else 0.0,
        "eligible_recall": round(tp / (tp + fn), 4) if tp + fn else 0.0,
        "false_eligible_rate": round(fp / (fp + tn), 4) if fp + tn else 0.0,
        "unsupported_claim_recall": round(detected / len(unsupported), 4),
        "unsupported_claim_detection_rate": round(detected / len(unsupported), 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def gates_pass(results: dict[str, float | int]) -> bool:
    """Both thresholds are mandatory; benchmark CLI returns nonzero on breach."""
    return (
        results["pairs"] >= MIN_CASES
        and results["false_eligible_rate"] <= MAX_FALSE_ELIGIBLE_RATE
        and results["unsupported_claim_recall"] >= MIN_UNSUPPORTED_CLAIM_RECALL
    )


if __name__ == "__main__":
    results = evaluate()
    print(json.dumps(results, indent=2))
    if not gates_pass(results):
        print("ERROR: adversarial benchmark did not meet release gates", file=sys.stderr)
        raise SystemExit(1)
