"""Contracts for source-driven research: test-first, no real award claims."""

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from scholaros.ingestion import OregonStudentAidConnector, PCCFoundationConnector
from scholaros.models import Decision
from scholaros.records import SourceSnapshot
from scholaros.research import analyze_snapshot, persist_public_snapshot, research_provider
from scholaros.storage import connect

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)


def snapshot(
    provider: str = "pcc", body: str = "F-1 students may apply. Deadline: 2027-02-01."
) -> SourceSnapshot:
    connector = PCCFoundationConnector() if provider == "pcc" else OregonStudentAidConnector()
    return SourceSnapshot.from_text(connector.url, body, NOW)


@pytest.mark.parametrize("provider", ["pcc", "osac"])
def test_program_source_is_never_auto_eligible(provider: str) -> None:
    report = analyze_snapshot(provider, snapshot(provider), now=NOW)
    assert report.decision is Decision.NEEDS_VERIFICATION
    assert report.verified_awards == 0
    assert report.ranked == ()
    assert any("individual" in reason.lower() for reason in report.review_reasons)
    assert all(item["source_url"] == snapshot(provider).source_url for item in report.candidates)


def test_every_candidate_has_exact_evidence_and_hash() -> None:
    saved = snapshot()
    report = analyze_snapshot("pcc", saved, now=NOW)
    assert report.candidates
    for item in report.candidates:
        assert item["quote"] in saved.text
        assert item["content_hash"] == sha256(saved.text.encode()).hexdigest()
        assert item["status"] == "unverified"


def test_negated_or_excluded_candidate_is_suppressed() -> None:
    for text in (
        "F-1 students may apply except applicants holding F-1 visas.",
        "F-1 students are eligible excluding international students.",
        "F-1 students are not eligible.",
    ):
        report = analyze_snapshot("pcc", snapshot(body=text), now=NOW)
        assert not any(x["field"] == "international" for x in report.candidates)
        assert report.decision is Decision.NEEDS_VERIFICATION


def test_mismatched_source_url_is_rejected() -> None:
    s = snapshot("pcc")
    with pytest.raises(ValueError, match="registry"):
        analyze_snapshot("osac", s, now=NOW)


def test_tampered_digest_is_rejected() -> None:
    s = snapshot()
    with pytest.raises(ValueError, match="digest"):
        analyze_snapshot("pcc", s.model_copy(update={"content_hash": "a" * 64}), now=NOW)


def test_stale_snapshot_flags_review_and_suppresses_candidates() -> None:
    s = snapshot()
    report = analyze_snapshot("pcc", s, now=NOW + timedelta(days=91))
    assert report.candidates == ()
    assert "source_stale" in report.review_reasons


def test_explicit_offline_mode_never_fetches(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Offline cache miss"):
        research_provider("pcc", cache_dir=tmp_path, now=NOW)


def test_invalid_provider_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown provider"):
        research_provider("unknown", cache_dir=tmp_path, now=NOW)


def test_snapshots_persist_without_applicant_records(tmp_path: Path) -> None:
    s = snapshot()
    with connect(tmp_path / "research.db") as db:
        persist_public_snapshot(db, s)
        row = db.execute(
            "SELECT source_url, content_hash, content_text FROM public_snapshots"
        ).fetchone()
        assert row == (s.source_url, s.content_hash, s.text)
        assert db.execute("SELECT count(*) FROM student_vault").fetchone()[0] == 0


def test_offline_cached_snapshot_has_no_verification_promotion(tmp_path: Path) -> None:
    saved = snapshot()
    cached = tmp_path / (sha256(saved.source_url.encode()).hexdigest() + ".json")
    cached.write_text(saved.model_dump_json(), encoding="utf-8")
    result = research_provider("pcc", cache_dir=tmp_path, now=NOW)
    assert result["decision"] == "needs_verification"
    assert result["source_origin"] == "offline_cache_untrusted"
    assert result["verified_awards"] == 0
    assert result["candidates"]


def test_cli_research_cached_requires_no_network(tmp_path: Path) -> None:
    saved = snapshot()
    cached = tmp_path / (sha256(saved.source_url.encode()).hexdigest() + ".json")
    cached.write_text(saved.model_dump_json(), encoding="utf-8")
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "scholaros",
            "research",
            "pcc",
            "--cache-dir",
            str(tmp_path),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(run.stdout)
    assert payload["decision"] == "needs_verification"
    assert payload["submission_status"] == "NOT_SUBMITTED"
    assert payload["verified_awards"] == 0


def test_cli_research_offline_cache_miss_is_helpful(tmp_path: Path) -> None:
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "scholaros",
            "research",
            "pcc",
            "--cache-dir",
            str(tmp_path),
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 2
    assert "Offline cache miss" in run.stderr
