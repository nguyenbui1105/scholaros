"""Evidence-anchored independent human adjudication and abstention-aware metrics.

Never infer gold from model predictions, or promote unreviewed web pages to
eligible. The annotations are external human assertions with source references.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .records import SourceSnapshot

Label = Literal["eligible", "ineligible", "unknown"]
DecisionLabel = Literal["eligible", "ineligible", "unknown", "needs_verification"]
FIELDS = ("visa", "school", "gpa", "deadline", "major")


class Annotation(BaseModel):
    """One reviewer records a *blind*, independently authored annotation."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    case_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    source_url: str
    content_hash: str = Field(min_length=64, max_length=64)
    decision: Label
    field_labels: dict[str, Label]
    evidence_quotes: dict[str, str]
    other_requirements_reviewed: bool = False
    annotated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_fields(self) -> Annotation:
        if set(self.field_labels) != set(FIELDS):
            raise ValueError("field_labels must contain exactly visa, school, gpa, deadline, major")
        if self.decision == "eligible" and (
            any(value != "eligible" for value in self.field_labels.values())
            or not self.other_requirements_reviewed
        ):
            raise ValueError("eligible requires five verified fields and other requirements")
        if self.decision == "ineligible" and "ineligible" not in self.field_labels.values():
            raise ValueError("ineligible requires at least one explicitly negative rule")
        if self.decision == "unknown" and (
            "unknown" not in self.field_labels.values()
            and self.other_requirements_reviewed
            and all(value == "eligible" for value in self.field_labels.values())
        ):
            raise ValueError("unknown must identify unresolved conditions")
        if self.annotated_at.tzinfo is None or self.annotated_at.utcoffset() is None:
            raise ValueError("annotated_at must be timezone-aware")
        return self


class Prediction(BaseModel):
    """Model output is separate from human gold and may abstain."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    case_id: str = Field(min_length=1)
    decision: DecisionLabel


class AdjudicatedCase(BaseModel):
    """Requires independent agreement or a distinct adjudicator."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    case_id: str
    source_url: str
    content_hash: str
    decision: Label
    reviewer_ids: tuple[str, ...]


def validate_annotation(annotation: Annotation, snapshot: SourceSnapshot) -> bool:
    """Fail closed when a known field has no exact supporting source excerpt."""
    # model_copy(update=...) bypasses Pydantic validation; revalidate on trust boundary.
    Annotation.model_validate(annotation.model_dump())
    if sha256(snapshot.text.encode("utf-8")).hexdigest() != snapshot.content_hash:
        raise ValueError("Snapshot hash does not match text")
    if (
        annotation.source_url != snapshot.source_url
        or annotation.content_hash != snapshot.content_hash
    ):
        raise ValueError("Annotation source URL/hash differs from the reviewed snapshot")
    for field in FIELDS:
        label = annotation.field_labels[field]
        quote = annotation.evidence_quotes.get(field, "")
        if label != "unknown" and (not quote.strip() or quote not in snapshot.text):
            raise ValueError(f"Missing or nonverbatim evidence quote for {field}")
    return True


def adjudicate(
    annotations: list[Annotation],
    snapshots: dict[str, SourceSnapshot],
    *,
    resolutions: dict[str, Annotation] | None = None,
) -> list[AdjudicatedCase]:
    """Two distinct annotators must agree on *all* fields, or a third adjudicates.

    Missing or conflicted cases are deliberately excluded, never treated as
    negative or eligible. Resolution reviewer must differ from both originals.
    """
    grouped: dict[str, list[Annotation]] = defaultdict(list)
    for item in annotations:
        if item.case_id not in snapshots:
            raise ValueError(f"Snapshot missing for {item.case_id!r}")
        validate_annotation(item, snapshots[item.case_id])
        grouped[item.case_id].append(item)

    result: list[AdjudicatedCase] = []
    for case_id, items in sorted(grouped.items()):
        # Duplicate reviewer IDs cannot manufacture consensus.
        independent = {item.reviewer_id: item for item in items}
        if len(independent) < 2:
            continue
        first, second = list(independent.values())[:2]
        agreement = (
            first.decision == second.decision
            and first.field_labels == second.field_labels
            and first.other_requirements_reviewed == second.other_requirements_reviewed
            and first.content_hash == second.content_hash
        )
        chosen = first
        reviewers = (first.reviewer_id, second.reviewer_id)
        if not agreement:
            third = (resolutions or {}).get(case_id)
            if third is None or third.reviewer_id in reviewers:
                continue
            validate_annotation(third, snapshots[case_id])
            # This record is a human adjudication, never generated from predictions.
            chosen = third
            reviewers = (*reviewers, third.reviewer_id)
        result.append(
            AdjudicatedCase(
                case_id=case_id,
                source_url=chosen.source_url,
                content_hash=chosen.content_hash,
                decision=chosen.decision,
                reviewer_ids=reviewers,
            )
        )
    return result


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def evaluate_predictions(
    gold: list[AdjudicatedCase], predictions: list[Prediction]
) -> dict[str, Any]:
    """Report coverage and false positives; undefined denominators remain None.

    Missing predictions -> needs_verification. Unknown gold is never silently
    promoted to a negative class in accuracy calculations, but predicted
    ELIGIBLE on unknown gold counts as an unsafe false-eligible.
    """
    keys = [prediction.case_id for prediction in predictions]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate prediction case_id")
    gold_keys = [item.case_id for item in gold]
    if len(gold_keys) != len(set(gold_keys)):
        raise ValueError("duplicate gold case_id")
    by_id = {p.case_id: p.decision for p in predictions}
    if set(by_id) - set(gold_keys):
        raise ValueError("Model predictions reference unknown gold cases")

    matrix: Counter[str] = Counter()
    for item in gold:
        pred = by_id.get(item.case_id, "needs_verification")
        matrix[f"{item.decision}->{pred}"] += 1

    n = len(gold)
    tp = matrix["eligible->eligible"]
    fp = sum(
        matrix[f"{status}->eligible"] for status in ("ineligible", "unknown")
    )
    fn = sum(
        matrix[f"eligible->{prediction}"]
        for prediction in ("ineligible", "unknown", "needs_verification")
    )
    noneligible = sum(item.decision != "eligible" for item in gold)
    abstentions = sum(
        count for key, count in matrix.items()
        if key.endswith("->unknown") or key.endswith("->needs_verification")
    )
    classified = n - abstentions
    correct_classified = tp + matrix["ineligible->ineligible"]
    return {
        "n_adjudicated": n,
        "n_predictions": len(predictions),
        "true_eligible": sum(item.decision == "eligible" for item in gold),
        "true_noneligible": noneligible,
        "eligible_precision": _ratio(tp, tp + fp),
        "eligible_recall": _ratio(tp, tp + fn),
        "false_eligible_rate": _ratio(fp, noneligible),
        "false_eligible_count": fp,
        "abstention_rate": _ratio(abstentions, n),
        "coverage": _ratio(classified, n),
        "selective_accuracy": _ratio(correct_classified, classified),
        "needs_verification_rate": _ratio(
            sum(v for k, v in matrix.items() if k.endswith("->needs_verification")), n
        ),
        "unknown_prediction_rate": _ratio(
            sum(v for k, v in matrix.items() if k.endswith("->unknown")), n
        ),
        "confusion": dict(sorted(matrix.items())),
        "scope": "adjudicated sources only; never equivalent to scholarship win probability",
    }
