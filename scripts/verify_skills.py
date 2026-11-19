"""Fail CI when an advertised skill lacks real implementation and tests."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
ALLOWED = {"specified", "implemented", "tested"}


def verify() -> list[str]:
    errors: list[str] = []
    for file in sorted(SKILLS.glob("*/SKILL.md")):
        text = file.read_text(encoding="utf-8")
        match = re.search(r"^status:\s*(\S+)", text, flags=re.MULTILINE)
        status = match.group(1) if match else ""
        if status not in ALLOWED:
            errors.append(f"{file}: invalid status {status!r}")
            continue
        if status in {"implemented", "tested"}:
            for field in ("implementation", "acceptance_fixture"):
                finding = re.search(rf"^{field}:\s*(.+)$", text, re.MULTILINE)
                path = ROOT / finding.group(1).strip() if finding else None
                if path is None or not path.is_file():
                    errors.append(f"{file}: missing {field}")
                elif field == "acceptance_fixture" and "def test_" not in path.read_text(encoding="utf-8"):
                    errors.append(f"{file}: fixture lacks runnable tests")
    if len(list(SKILLS.glob("*/SKILL.md"))) != 20:
        errors.append("Expected 20 skill contracts")
    return errors


if __name__ == "__main__":
    problems = verify()
    for issue in problems:
        print(issue, file=sys.stderr)
    if problems:
        raise SystemExit(1)
    print("20 contracts verified; implemented/tested labels have code and tests")
