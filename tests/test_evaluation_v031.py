"""Contract tests for independent real-source adjudication and honest metrics."""

from datetime import UTC, datetime

import pytest

from scholaros.evaluation import (
    Annotation,
    Prediction,
    adjudicate,
    evaluate_predictions,
    validate_annotation,
)
from scholaros.records import SourceSnapshot

DATE = datetime(2026, 11, 19, tzinfo=UTC)
URL = "https://example.edu/scholarship"
TEXT = (
    "F-1 students may apply. Demo College students may apply. "
    "Computer science majors may apply. Minimum GPA 3.0. Deadline: 2027-05-01."
)


def snapshot() -> SourceSnapshot:
    return SourceSnapshot.from_text(URL, TEXT, DATE)


QUOTES = {
    "visa": "F-1 students may apply",
    "school": "Demo College students may apply",
    "major": "Computer science majors may apply",
    "gpa": "Minimum GPA 3.0",
    "deadline": "Deadline: 2027-05-01",
}


def label(
    reviewer: str,
    *,
    case_id: str = "synthetic-1",
    decision: str = "eligible",
    quotes: dict[str, str] | None = None,
) -> Annotation:
    return Annotation(
        case_id=case_id,
        reviewer_id=reviewer,
        source_url=URL,
        content_hash=snapshot().content_hash,
        decision=decision,
        field_labels={key: "eligible" for key in QUOTES},
        evidence_quotes=QUOTES if quotes is None else quotes,
        other_requirements_reviewed=True,
    )


def test_valid_evidence_and_consensus() -> None:
    first, second = label("human-a"), label("human-b")
    assert validate_annotation(first, snapshot())
    adjudicated = adjudicate([first, second], {"synthetic-1": snapshot()})
    assert len(adjudicated) == 1
    assert adjudicated[0].decision == "eligible"


def test_one_reviewer_not_gold() -> None:
    assert adjudicate([label("a")], {"synthetic-1": snapshot()}) == []


def test_duplicate_reviewers_not_independent() -> None:
    assert adjudicate([label("a"), label("a")], {"synthetic-1": snapshot()}) == []


def test_mismatched_content_hash_is_rejected() -> None:
    bad = label("a").model_copy(update={"content_hash": "f" * 64})
    with pytest.raises(ValueError, match="hash"):
        validate_annotation(bad, snapshot())


def test_nonverbatim_quote_is_rejected() -> None:
    bad_quotes = dict(QUOTES)
    bad_quotes["gpa"] = "Minimum GPA 4.0"
    with pytest.raises(ValueError, match="quote"):
        validate_annotation(label("a", quotes=bad_quotes), snapshot())


def test_disagreement_is_not_silent_gold() -> None:
    a = label("a")
    b = label("b").model_copy(
        update={
            "decision": "unknown",
            "field_labels": {**label("b").field_labels, "visa": "unknown"},
            "other_requirements_reviewed": False,
        }
    )
    assert adjudicate([a, b], {"synthetic-1": snapshot()}) == []


def test_eligible_requires_all_known_fields_with_evidence() -> None:
    bad = label("a").model_copy(
        update={"field_labels": {**label("a").field_labels, "gpa": "unknown"}}
    )
    with pytest.raises(ValueError, match="eligible"):
        validate_annotation(bad, snapshot())


def test_predictions_do_not_depend_on_gold() -> None:
    gold = adjudicate([label("a"), label("b")], {"synthetic-1": snapshot()})
    results = evaluate_predictions(gold, [Prediction(case_id="synthetic-1", decision="eligible")])
    assert results["eligible_precision"] == 1.0
    assert results["eligible_recall"] == 1.0
    assert results["false_eligible_count"] == 0
    assert results["abstention_rate"] == 0.0


def test_no_gold_is_unmeasured_not_perfect() -> None:
    metrics = evaluate_predictions([], [])
    assert metrics["eligible_precision"] is None
    assert metrics["eligible_recall"] is None
    assert metrics["false_eligible_rate"] is None
    assert metrics["n_adjudicated"] == 0


def test_missing_prediction_counts_as_abstention() -> None:
    gold = adjudicate([label("a"), label("b")], {"synthetic-1": snapshot()})
    metrics = evaluate_predictions(gold, [])
    assert metrics["abstention_rate"] == 1.0
    assert metrics["eligible_recall"] == 0.0
    assert metrics["eligible_precision"] is None


def test_false_eligible_is_measured() -> None:
    source = snapshot().text.replace("F-1 students may apply", "F-1 students are ineligible")
    negative_snapshot = SourceSnapshot.from_text(URL, source, DATE)
    neg = label("a").model_copy(
        update={
            "content_hash": negative_snapshot.content_hash,
            "field_labels": {**label("a").field_labels, "visa": "ineligible"},
            "evidence_quotes": {**QUOTES, "visa": "F-1 students are ineligible"},
        }
    )
    neg2 = neg.model_copy(update={"reviewer_id": "b"})
    gold = adjudicate([neg, neg2], {"synthetic-1": negative_snapshot})
    metrics = evaluate_predictions(gold, [Prediction(case_id="synthetic-1", decision="eligible")])
    assert metrics["false_eligible_count"] == 1
    assert metrics["false_eligible_rate"] == 1.0
    assert metrics["eligible_precision"] == 0.0


def test_duplicate_predictions_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        evaluate_predictions(
            [],
            [
                Prediction(case_id="a", decision="unknown"),
                Prediction(case_id="a", decision="unknown"),
            ],
        )
