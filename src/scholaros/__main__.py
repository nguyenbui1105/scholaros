"""ScholarOS CLI: offline fictional-data workflows and local vault operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .storage import connect, export_schemas, purge_student
from .workflow import run_stage


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="scholaros", description="Evidence-first scholarship research (synthetic offline beta)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("demo", "ingest", "match", "rank", "draft", "review", "packet", "explain"):
        item = sub.add_parser(name)
        item.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
        item.add_argument("--scenario", type=Path, help="SYNTHETIC scenario JSON")
        item.add_argument("--fixture", type=Path, help="Recorded synthetic HTML fixture")
        if name == "explain":
            item.add_argument("opportunity_id")
        if name in {"review", "packet"}:
            item.add_argument("--text", help="Draft text to check against confirmed evidence")
    init = sub.add_parser("init")
    init.add_argument("--json", action="store_true")
    init.add_argument("--db", type=Path, default=Path(".scholaros/scholaros.db"))
    schemas = sub.add_parser("schemas")
    schemas.add_argument("--json", action="store_true")
    schemas.add_argument("--out", type=Path, default=Path("docs/schemas"))
    purge = sub.add_parser("purge")
    purge.add_argument("--json", action="store_true")
    purge.add_argument("--db", type=Path, default=Path(".scholaros/scholaros.db"))
    purge.add_argument("student_id")
    args = parser.parse_args()
    try:
        result: dict[str, Any]
        if args.command == "init":
            with connect(args.db):
                pass
            result = {"database": str(args.db), "initialized": True}
        elif args.command == "schemas":
            export_schemas(args.out)
            result = {"exported_to": str(args.out)}
        elif args.command == "purge":
            with connect(args.db) as db:
                count = purge_student(db, args.student_id)
            result = {"student_id": args.student_id, "deleted": count}
        else:
            result = run_stage(
                args.command,
                scenario_path=args.scenario,
                html_path=args.fixture,
                opportunity_id=getattr(args, "opportunity_id", None),
                submitted_text=getattr(args, "text", None),
            )
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print("ScholarOS synthetic offline workflow — NOT REAL scholarship data")
            print(json.dumps(result, indent=2, default=str))
    except (OSError, ValueError, PermissionError, RuntimeError, KeyError) as exc:
        print(f"ScholarOS error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
