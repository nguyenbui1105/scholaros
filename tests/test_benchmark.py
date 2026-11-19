from scholaros.benchmark import (
    MAX_FALSE_ELIGIBLE_RATE,
    MIN_CASES,
    MIN_UNSUPPORTED_CLAIM_RECALL,
    evaluate,
    gates_pass,
)


def test_labeled_adversarial_benchmark_release_gates() -> None:
    result = evaluate()
    assert result["pairs"] >= MIN_CASES >= 60
    assert result["false_eligible_rate"] == MAX_FALSE_ELIGIBLE_RATE == 0.0
    assert result["unsupported_claim_recall"] >= MIN_UNSUPPORTED_CLAIM_RECALL
    assert gates_pass(result)
    assert result["eligible_precision"] == 1.0
    assert result["eligible_recall"] == 1.0
    assert result["exact_state_accuracy"] == 1.0


def test_benchmark_gate_rejects_false_eligible() -> None:
    results = evaluate()
    results["false_eligible_rate"] = 0.01
    assert not gates_pass(results)


def test_benchmark_gate_rejects_low_unsupported_recall() -> None:
    results = evaluate()
    results["unsupported_claim_recall"] = MIN_UNSUPPORTED_CLAIM_RECALL - 0.01
    assert not gates_pass(results)
