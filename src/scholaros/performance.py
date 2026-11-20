"""Reproducible offline stage timings; real API cost only from reported token usage."""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class LLMUsage:
    provider: str
    model: str
    input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise ValueError("Token usage cannot be negative")


def calculate_llm_cost(
    usage: LLMUsage,
    *,
    input_usd_per_million: float | None = None,
    output_usd_per_million: float | None = None,
) -> float | None:
    """No price assumptions: omit currency amounts without explicit rate data."""
    if input_usd_per_million is None or output_usd_per_million is None:
        return None
    if (
        not math.isfinite(input_usd_per_million)
        or not math.isfinite(output_usd_per_million)
        or input_usd_per_million < 0
        or output_usd_per_million < 0
    ):
        raise ValueError("Usage prices must be finite nonnegative amounts")
    return round(
        (
            usage.input_tokens * input_usd_per_million
            + usage.output_tokens * output_usd_per_million
        ) / 1_000_000,
        8,
    )


def percentile(values: list[float], percent: float) -> float:
    """Nearest-rank percentile. p95 is max for a sample of 20 or fewer."""
    if not values or not 0 <= percent <= 100:
        raise ValueError("Percentile requires nonempty sample and 0 <= percent <= 100")
    sorted_values = sorted(values)
    rank = max(1, math.ceil(len(sorted_values) * percent / 100))
    return sorted_values[rank - 1]


def benchmark_stages(
    stages: Mapping[str, Callable[[], object]],
    *,
    repetitions: int = 100,
    warmup: int = 3,
) -> dict[str, Any]:
    """Measure sequential offline stage latencies without network/LLM calls.

    The closures are supplied by the caller, which must guarantee no network,
    side effects, or API calls. This reports elapsed wall time, not CPU time.
    """
    if repetitions < 1 or warmup < 0 or not stages:
        raise ValueError("Specify >=1 repetitions, >=0 warmup, and nonempty stages")
    for _ in range(warmup):
        for work in stages.values():
            work()
    results: dict[str, list[float]] = {name: [] for name in stages}
    total_start = time.perf_counter_ns()
    for _ in range(repetitions):
        for name, work in stages.items():
            start = time.perf_counter_ns()
            work()
            end = time.perf_counter_ns()
            results[name].append((end - start) / 1_000_000)
    elapsed_s = max((time.perf_counter_ns() - total_start) / 1_000_000_000, 1e-9)
    return {
        "repetitions": repetitions,
        "elapsed_seconds": round(elapsed_s, 6),
        "throughput_operations_per_second": round(repetitions / elapsed_s, 3),
        "network_calls": 0,
        "llm_calls": 0,
        "llm_cost_usd": None,
        "latency_unit": "milliseconds",
        "percentile_method": "nearest_rank",
        "stages": {
            name: {
                "n": len(samples),
                "p50_ms": round(percentile(samples, 50), 6),
                "p95_ms": round(percentile(samples, 95), 6),
                "mean_ms": round(mean(samples), 6),
            }
            for name, samples in results.items()
        },
    }
