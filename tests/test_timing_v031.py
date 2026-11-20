"""Deterministic latency estimator and explicit LLM rate/usage controls."""

import pytest

from scholaros.performance import (
    LLMUsage,
    benchmark_stages,
    calculate_llm_cost,
    percentile,
)


def test_percentile_nearest_rank() -> None:
    assert percentile([1, 2, 3, 4, 5], 50) == 3
    assert percentile([1, 2, 3, 4, 5], 95) == 5


def test_benchmark_captures_stage_p50_p95_and_throughput() -> None:
    phases = {"ingest": lambda: "text", "extract": lambda: 2, "match": lambda: "needs_verification"}
    report = benchmark_stages(phases, repetitions=8)
    assert report["repetitions"] == 8
    assert report["throughput_operations_per_second"] > 0
    for name in phases:
        assert report["stages"][name]["p95_ms"] >= report["stages"][name]["p50_ms"]
    assert report["network_calls"] == 0


def test_invalid_repetitions() -> None:
    with pytest.raises(ValueError):
        benchmark_stages({"ingest": lambda: None}, repetitions=0)


def test_unknown_llm_prices_are_not_invented() -> None:
    usage = LLMUsage(provider="mock", model="deterministic", input_tokens=50, output_tokens=20)
    assert calculate_llm_cost(usage) is None


def test_explicit_rates_calculate_cost() -> None:
    usage = LLMUsage(
        provider="example", model="test", input_tokens=1_000_000, output_tokens=500_000
    )
    assert calculate_llm_cost(usage, input_usd_per_million=2.0, output_usd_per_million=8.0) == 6.0
