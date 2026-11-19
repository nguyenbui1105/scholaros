from scholaros.benchmark import evaluate


def test_labeled_benchmark_has_no_false_eligible() -> None:
    result = evaluate()
    assert result["pairs"] >= 30
    assert result["false_eligible_rate"] == 0.0
    assert result["eligible_precision"] == 1.0
    assert result["eligible_recall"] == 1.0
    assert result["exact_state_accuracy"] == 1.0


def test_unsupported_claim_detection() -> None:
    result = evaluate()
    assert result["unsupported_claim_detection_rate"] == 1.0
