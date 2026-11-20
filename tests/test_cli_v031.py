"""CLI end-to-end tests: no network, no real applicant PII, no invented gold."""

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from scholaros.records import SourceSnapshot


def run_cli(*args: str) -> dict[str, object]:
    done = subprocess.run(
        [sys.executable, "-m", "scholaros", *args, "--json"],
        capture_output=True, text=True, check=True,
    )
    result = json.loads(done.stdout)
    assert isinstance(result, dict)
    return result


def test_perf_reports_stage_times_without_network() -> None:
    result = run_cli("perf", "--repetitions", "8")
    assert result["network_calls"] == 0
    assert result["llm_cost_usd"] is None
    assert result["stages"]["extract_rule_candidates"]["p95_ms"] >= 0


def test_real_eval_with_empty_gold_is_unmeasured(tmp_path: Path) -> None:
    annotations = tmp_path / "annotations.jsonl"
    predictions = tmp_path / "predictions.jsonl"
    annotations.write_text("", encoding="utf-8")
    predictions.write_text("", encoding="utf-8")
    result = run_cli(
        "eval-real", "--annotations", str(annotations), "--predictions",
        str(predictions), "--snapshots", str(tmp_path),
    )
    assert result["n_adjudicated"] == 0
    assert result["eligible_precision"] is None
    assert result["false_eligible_rate"] is None
    assert result["n_unadjudicated"] == 0


def test_discovery_creates_unapproved_candidates(tmp_path: Path) -> None:
    source = tmp_path / "index.html"
    output = tmp_path / "candidates.json"
    source.write_text(
        '<a href="/scholarships/stem">A</a><a href="/login">Login</a>',
        encoding="utf-8",
    )
    result = run_cli(
        "discover", "--base-url", "https://example.edu/scholarships/",
        "--html", str(source), "--out", str(output),
    )
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert result["candidate_urls"] == 1
    assert result["validated_official_pages"] == 0
    assert not manifest["approved_by_operator"]


def test_audit_offline_does_not_infer_real_labels(tmp_path: Path) -> None:
    snap = SourceSnapshot.from_text(
        "https://example.edu/scholarship", "SYNTHETIC ONLY",
        datetime(2026, 11, 19, tzinfo=UTC),
    )
    (tmp_path / "test.json").write_text(snap.model_dump_json(), encoding="utf-8")
    result = run_cli(
        "audit-corpus", "--snapshots", str(tmp_path), "--min-pages", "1",
    )
    assert result["snapshots_validated"] == 1
    assert result["official_pages_human_verified"] == 0


def test_collect_never_runs_without_approval(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({
            "approved_by_operator": False,
            "terms_checked": False,
            "candidates": [{"url": "https://example.edu/scholarships/1"}],
        }), encoding="utf-8",
    )
    done = subprocess.run(
        [sys.executable, "-m", "scholaros", "collect",
         "--manifest", str(manifest), "--cache-dir", str(tmp_path / "cache"), "--json"],
        capture_output=True, text=True,
    )
    assert done.returncode != 0
    assert "approval" in done.stderr.lower()
