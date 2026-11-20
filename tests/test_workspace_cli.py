"""Black-box onboarding → agent coordination → review → approval, fully offline."""

import json
import os
import subprocess
import sys
from pathlib import Path

from cryptography.fernet import Fernet


def run_cli(*args: str, env: dict[str, str]) -> dict[str, object]:
    run = subprocess.run(
        [sys.executable, "-m", "scholaros", *args, "--json"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    data = json.loads(run.stdout)
    assert isinstance(data, dict)
    return data


def test_user_can_onboard_and_run_agents_offline(tmp_path: Path) -> None:
    env = {**os.environ, "SCHOLAROS_FERNET_KEY": Fernet.generate_key().decode()}
    profile_path = tmp_path / "student.enc"
    output_path = tmp_path / "packets.enc"
    created = run_cli(
        "onboard",
        "--profile-json",
        "examples/agent_demo_profile.json",
        "--out",
        str(profile_path),
        env=env,
    )
    assert created["saved_encrypted"]
    assert profile_path.exists()
    assert b"F-1" not in profile_path.read_bytes()
    run = run_cli(
        "autopilot",
        "--vault",
        str(profile_path),
        "--catalog",
        "examples/agent_demo_catalog.json",
        "--out",
        str(output_path),
        "--today",
        "2026-11-20",
        env=env,
    )
    assert run["packets_created"] == 1
    assert run["actual_submissions"] == 0
    assert run["fixture_only"]
    status = run_cli("workspace", "--file", str(output_path), env=env)
    item = status["applications"][0]
    assert item["submission_status"] == "NOT_SUBMITTED"
    assert not item["approved"]
    verified = run_cli(
        "approve-packet",
        "--file",
        str(output_path),
        "--packet-id",
        item["id"],
        "--hash",
        item["packet_hash"],
        "--yes",
        env=env,
    )
    assert verified["approved_for_manual_review"]
    assert verified["submission_status"] == "NOT_SUBMITTED"
    after = run_cli("workspace", "--file", str(output_path), env=env)
    assert after["applications"][0]["approved"]


def test_agent_run_without_encryption_key_fails(tmp_path: Path) -> None:
    env = dict(os.environ)
    env.pop("SCHOLAROS_FERNET_KEY", None)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scholaros",
            "onboard",
            "--profile-json",
            "examples/agent_demo_profile.json",
            "--out",
            str(tmp_path / "student.enc"),
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 2
    assert "SCHOLAROS_FERNET_KEY" in proc.stderr


def test_invalid_approval_cannot_pass(tmp_path: Path) -> None:
    env = {**os.environ, "SCHOLAROS_FERNET_KEY": Fernet.generate_key().decode()}
    profile_path = tmp_path / "student.enc"
    output_path = tmp_path / "packets.enc"
    run_cli(
        "onboard",
        "--profile-json",
        "examples/agent_demo_profile.json",
        "--out",
        str(profile_path),
        env=env,
    )
    run_cli(
        "autopilot",
        "--vault",
        str(profile_path),
        "--out",
        str(output_path),
        "--today",
        "2026-11-20",
        env=env,
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scholaros",
            "approve-packet",
            "--file",
            str(output_path),
            "--packet-id",
            "fictional-stem",
            "--hash",
            "0" * 64,
            "--yes",
            "--json",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode != 0
    assert "mismatch" in proc.stderr


def test_importing_unconsented_profile_refused(tmp_path: Path) -> None:
    env = {**os.environ, "SCHOLAROS_FERNET_KEY": Fernet.generate_key().decode()}
    profile = json.loads(Path("examples/agent_demo_profile.json").read_text())
    profile["student"]["consent_to_store"] = False
    source = tmp_path / "student.json"
    source.write_text(json.dumps(profile), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "scholaros", "onboard", "--profile-json", str(source)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 2
    assert "consent" in proc.stderr.lower()
