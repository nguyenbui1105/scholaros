import json
import subprocess
import sys
from pathlib import Path

import pytest

from scholaros.workflow import build_synthetic, run_stage


def invoke(*arguments: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-m", "scholaros", *arguments, "--json"],
        check=True, capture_output=True, text=True,
    )
    return json.loads(completed.stdout)


def test_end_to_end_fictional_fixture() -> None:
    data = invoke("demo")
    assert data["fixture_only"]
    assert data["decision"] == "eligible"
    assert data["ranked"]
    assert data["review"] == []
    assert data["submission_status"] == "NOT_SUBMITTED"


@pytest.mark.parametrize("stage", ["ingest", "match", "rank", "draft", "review", "packet"])
def test_stages(stage: str) -> None:
    assert invoke(stage)["fixture_only"]


def test_missing_rule_fails_closed(tmp_path: Path) -> None:
    fixture = tmp_path / "incomplete.html"
    fixture.write_text("<html>F-1 students may apply</html>", encoding="utf-8")
    with pytest.raises(ValueError, match="missing explicitly quoted rules"):
        build_synthetic(html_path=fixture)


def test_unsupported_claim_in_packet() -> None:
    data = run_stage("packet", submitted_text="I won a Nobel Prize.")
    assert not data["packet"]["ready_for_submission"]
    assert data["packet"]["unsupported_claims"]


def test_explain_unknown_id_errors() -> None:
    with pytest.raises(ValueError):
        run_stage("explain", opportunity_id="not-found")


def test_schemas_cli(tmp_path: Path) -> None:
    data = invoke("schemas", "--out", str(tmp_path))
    assert (tmp_path / "Opportunity.schema.json").exists()
    assert data["exported_to"] == str(tmp_path)


def test_init_and_purge(tmp_path: Path) -> None:
    db = tmp_path / "demo.db"
    assert invoke("init", "--db", str(db))["initialized"]
    assert invoke("purge", "--db", str(db), "synthetic-student")["deleted"] == 0
