"""Direct in-process tests for encrypted applicant onboarding and agent commands."""

import json
from datetime import date
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from scholaros.workspace_cli import (
    approve,
    enroll,
    execute,
    inspect,
    interactive_intake,
)


def test_interactive_intake_uses_minimal_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answers = iter(
        [
            "local-id",
            "Demo College",
            "F-1",
            "undergraduate",
            "computer science, mathematics",
            "3.7",
            "I built a school project.",
            "YES",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    result = interactive_intake()
    assert result.student.student_id == "local-id"
    assert result.student.majors == ("computer science", "mathematics")
    assert result.student.consent_to_store
    assert len(result.evidence) == 1
    assert result.evidence[0].confirmed_by_student


def test_interactive_missing_fields_preserve_unknowns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answers = iter(["anonymous", "", "", "", "", "", "", "YES"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    result = interactive_intake()
    assert result.student.gpa is None
    assert result.student.majors == ()
    assert result.student.visa_status is None
    assert result.evidence == []


def test_direct_onboard_autopilot_inspect_and_approve(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCHOLAROS_FERNET_KEY", Fernet.generate_key().decode())
    private = tmp_path / "student.enc"
    packets = tmp_path / "packets.enc"
    result = enroll(private, profile_json=Path("examples/agent_demo_profile.json"))
    assert result["saved_encrypted"] is True
    assert result["evidence_items"] == 2

    run = execute(
        private,
        Path("examples/agent_demo_catalog.json"),
        packets,
        today=date(2026, 11, 20),
    )
    assert run["packets_created"] == 1
    assert run["fixture_only"] is True
    assert run["actual_submissions"] == 0
    summary = inspect(packets)
    assert summary["privacy"].startswith("Redacted")
    assert "student_id" not in summary

    private_review = inspect(packets, reveal=True)
    assert private_review["student_id"] == "synthetic-demo"
    packet = private_review["applications"][0]
    updated = approve(
        packets,
        packet_id=packet["id"],
        packet_hash=packet["packet_hash"],
        student_confirmed=True,
    )
    assert updated["approved_for_manual_review"]
    assert inspect(packets)["applications"][0]["approved"] is True


def test_direct_wrong_hash_denied_without_changing_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCHOLAROS_FERNET_KEY", Fernet.generate_key().decode())
    profile = tmp_path / "profile.enc"
    output = tmp_path / "out.enc"
    enroll(profile, profile_json=Path("examples/agent_demo_profile.json"))
    execute(profile, Path("examples/agent_demo_catalog.json"), output, today=date(2026, 11, 20))
    with pytest.raises(PermissionError):
        approve(output, packet_id="fictional-stem", packet_hash="f" * 64, student_confirmed=True)
    assert inspect(output)["applications"][0]["approved"] is False


def test_bad_catalog_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCHOLAROS_FERNET_KEY", Fernet.generate_key().decode())
    profile = tmp_path / "profile.enc"
    catalog = tmp_path / "catalog.json"
    enroll(profile, profile_json=Path("examples/agent_demo_profile.json"))
    catalog.write_text(json.dumps({"opportunities": "invalid"}), encoding="utf-8")
    with pytest.raises(ValueError, match="opportunities list"):
        execute(profile, catalog, tmp_path / "out.enc", today=date(2026, 11, 20))
