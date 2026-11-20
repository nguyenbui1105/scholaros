"""Offline CLI entrypoints for blind adjudication and performance measurement."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from .collection import (
    CollectionManifest,
    collect_authorized,
    collect_offline,
    discover_links,
    load_manifest,
    save_candidates,
)
from .eligibility import assess_eligibility
from .evaluation import Annotation, Prediction, adjudicate, evaluate_predictions
from .ingestion import extract_candidates, html_to_text
from .performance import LLMUsage, benchmark_stages, calculate_llm_cost
from .records import SourceSnapshot
from .workflow import HTML, build_synthetic


def _read_lines(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parsed: Any = json.loads(line)
        if not isinstance(parsed, dict):
            raise ValueError(f"{path}:{line_number}: expected a JSON object")
        rows.append(parsed)
    return rows


def evaluate_files(
    annotations_path: Path,
    predictions_path: Path,
    snapshots_dir: Path,
    *,
    resolutions_path: Path | None = None,
) -> dict[str, Any]:
    """Never label, train, infer or edit gold from predictions.

    Annotators work from source snapshots independently; predictions are loaded
    only *after* the gold consensus has been checked.
    """
    annotations = [Annotation.model_validate(record) for record in _read_lines(annotations_path)]
    ids = {item.case_id for item in annotations}
    snapshots = {
        case_id: SourceSnapshot.model_validate_json(
            (snapshots_dir / f"{case_id}.json").read_text(encoding="utf-8")
        )
        for case_id in ids
    }
    resolutions = (
        {row["case_id"]: Annotation.model_validate(row) for row in _read_lines(resolutions_path)}
        if resolutions_path is not None
        else None
    )
    consensus = adjudicate(annotations, snapshots, resolutions=resolutions)
    predictions = [Prediction.model_validate(record) for record in _read_lines(predictions_path)]
    result = evaluate_predictions(consensus, predictions)
    result["n_annotation_records"] = len(annotations)
    result["n_cases_with_source"] = len(snapshots)
    result["n_unadjudicated"] = len(ids) - len(consensus)
    result["benchmark_type"] = "real-source annotations only if independently reviewed"
    return result


def benchmark_offline(
    *,
    repetitions: int = 100,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    input_rate: float | None = None,
    output_rate: float | None = None,
) -> dict[str, Any]:
    """Measure offline synthetic HTML, extraction and a full eligibility check."""
    student, opportunity, _, _, _ = build_synthetic(today=date(2026, 11, 18))
    html = HTML.read_text(encoding="utf-8")
    source_text = html_to_text(html)
    snapshot = SourceSnapshot.from_text(
        opportunity.official_url, source_text, datetime(2026, 11, 18, tzinfo=UTC)
    )
    stages = {
        "ingest_html_normalization": lambda: html_to_text(html),
        "extract_rule_candidates": lambda: extract_candidates(snapshot),
        "match_synthetic_eligibility": lambda: assess_eligibility(
            student, opportunity, today=date(2026, 11, 18)
        ),
    }
    result = benchmark_stages(stages, repetitions=repetitions)
    result["measurement_scope"] = "offline synthetic fixture; no live network or real LLM"
    if input_tokens is not None and output_tokens is not None:
        usage = LLMUsage(
            provider="operator-supplied",
            model="operator-supplied",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        result["llm_cost_usd"] = calculate_llm_cost(
            usage, input_usd_per_million=input_rate, output_usd_per_million=output_rate
        )
        result["llm_cost_basis"] = "caller-provided measured tokens and caller-provided rates"
    return result


def discover_from_saved_html(base_url: str, html_path: Path, out: Path) -> dict[str, Any]:
    links = discover_links(base_url, html_path.read_text(encoding="utf-8"))
    save_candidates(out, links, discovered_from=base_url)
    return {
        "candidate_urls": len(links),
        "validated_official_pages": 0,
        "independent_gold_labels": 0,
        "manifest_path": str(out),
        "status": "unreviewed_candidates",
    }


def collect_from_manifest(
    manifest_path: Path,
    cache_dir: Path,
    *,
    allow_network: bool,
    min_pages: int = 50,
) -> dict[str, Any]:
    manifest: CollectionManifest = load_manifest(manifest_path)
    return {
        **collect_authorized(
            manifest,
            cache_dir=cache_dir,
            allow_network=allow_network,
            min_pages=min_pages,
        ),
        "status": "snapshot_audit_only",
    }


def audit_offline_dir(path: Path, *, min_pages: int = 50) -> dict[str, int]:
    return collect_offline(sorted(path.glob("*.json")), min_pages=min_pages)
