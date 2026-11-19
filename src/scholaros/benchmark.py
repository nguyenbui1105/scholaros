"""Labeled synthetic eligibility and unsupported-claim benchmark."""
from __future__ import annotations

import csv
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

from .eligibility import assess_eligibility
from .models import Decision, Student
from .records import EvidenceItem
from .workflow import ROOT, build_synthetic
from .writing import review_claims


def _change_student(person: Student, field: str, value: str) -> Student:
    if field == "academic_level":
        return replace(person, academic_level=None if value == "NONE" else value)
    if field == "visa_status":
        return replace(person, visa_status=None if value == "NONE" else value)
    if field == "majors":
        return replace(person, majors=None if value == "NONE" else [value])
    if field == "school":
        return replace(person, school=None if value == "NONE" else value)
    if field == "gpa":
        return replace(person, gpa=None if value == "NONE" else float(value))
    raise ValueError(f"Unexpected benchmark field {field}")


def evaluate(path: Path | None = None) -> dict[str, float | int]:
    source = path or ROOT / "examples" / "benchmark_36.csv"
    with source.open(newline="", encoding="utf-8") as handle:
        cases = list(csv.DictReader(handle))
    if len(cases) < 30:
        raise ValueError("At least 30 labeled pairs are required")
    tp = fp = fn = tn = correct = 0
    for row in cases:
        person, award, _, _, _ = build_synthetic()
        modified = _change_student(person, row["field"], row["value"])
        predicted = assess_eligibility(modified, award, today=award.verified_on or date.today()).decision
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
    unsupported = [f"I received fictional award number {i}." for i in range(10)]
    detected = sum(
        not review_claims(statement, evidence).is_clean for statement in unsupported
    )
    return {
        "pairs": len(cases),
        "exact_state_accuracy": round(correct / len(cases), 4),
        "eligible_precision": round(tp / (tp + fp), 4) if tp + fp else 0.0,
        "eligible_recall": round(tp / (tp + fn), 4) if tp + fn else 0.0,
        "false_eligible_rate": round(fp / (fp + tn), 4) if fp + tn else 0.0,
        "unsupported_claim_detection_rate": round(detected / len(unsupported), 4),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
