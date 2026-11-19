import json
import sys
from pathlib import Path

import pytest

from scholaros.__main__ import main


@pytest.mark.parametrize(
    "command",
    [
        "demo",
        "ingest",
        "match",
        "rank",
        "draft",
        "review",
        "packet",
        "explain",
    ],
)
def test_cli_functions_in_process(
    command: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = ["scholaros", command]
    if command == "explain":
        args.append("fictional-stem-award")
    args.append("--json")
    monkeypatch.setattr(sys, "argv", args)
    main()
    result = json.loads(capsys.readouterr().out)
    assert result["fixture_only"] is True


def test_cli_admin_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db = tmp_path / "db.sqlite"
    for args in (
        ["init", "--db", str(db)],
        ["purge", "--db", str(db), "synthetic-student"],
        ["schemas", "--out", str(tmp_path / "schemas")],
    ):
        monkeypatch.setattr(sys, "argv", ["scholaros", *args, "--json"])
        main()
        assert json.loads(capsys.readouterr().out)
    assert (tmp_path / "schemas" / "Opportunity.schema.json").exists()


def test_cli_catches_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["scholaros", "explain", "missing"])
    with pytest.raises(SystemExit) as info:
        main()
    assert info.value.code == 2
    assert "No fictional opportunity" in capsys.readouterr().err
