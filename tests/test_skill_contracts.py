import importlib.util
from pathlib import Path


def test_skill_contract_validator() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "verify_skills", root / "scripts" / "verify_skills.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.verify() == []


def test_universal_envelope_schema_exists() -> None:
    import json
    root = Path(__file__).resolve().parents[1]
    schema = json.loads(
        (root / "docs" / "schemas" / "universal-envelope.schema.json").read_text()
    )
    assert set(schema["$defs"]) == {"input", "output"}
