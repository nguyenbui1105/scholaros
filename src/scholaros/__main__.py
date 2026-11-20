"""ScholarOS CLI: offline fictional-data workflows and local vault operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .evaluation_cli import (
    audit_offline_dir,
    benchmark_offline,
    collect_from_manifest,
    discover_from_saved_html,
    evaluate_files,
)
from .research import research_provider
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
    research = sub.add_parser(
        "research", help="Inspect a registered public application page (no eligibility promotion)"
    )
    research.add_argument("provider", choices=["pcc", "osac"])
    research.add_argument("--json", action="store_true")
    research.add_argument("--cache-dir", type=Path, default=Path(".scholaros/cache"))
    research.add_argument(
        "--allow-network", action="store_true", help="Opt-in robots-aware official fetch"
    )
    research.add_argument("--db", type=Path, help="Optional local public-source SQLite store")
    evaluation = sub.add_parser("eval-real", help="Evaluate independently adjudicated records")
    evaluation.add_argument("--annotations", type=Path, required=True)
    evaluation.add_argument("--predictions", type=Path, required=True)
    evaluation.add_argument("--snapshots", type=Path, required=True)
    evaluation.add_argument("--resolutions", type=Path)
    evaluation.add_argument("--json", action="store_true")
    performance = sub.add_parser("perf", help="Benchmark synthetic offline pipeline timings")
    performance.add_argument("--repetitions", type=int, default=100)
    performance.add_argument("--input-tokens", type=int)
    performance.add_argument("--output-tokens", type=int)
    performance.add_argument("--input-rate", type=float)
    performance.add_argument("--output-rate", type=float)
    performance.add_argument("--json", action="store_true")
    discover = sub.add_parser("discover", help="Extract unreviewed URLs from saved public HTML")
    discover.add_argument("--base-url", required=True)
    discover.add_argument("--html", type=Path, required=True)
    discover.add_argument("--out", type=Path, required=True)
    discover.add_argument("--json", action="store_true")
    collect = sub.add_parser("collect", help="Opt-in provider-authorized 50–100 page snapshot job")
    collect.add_argument("--manifest", type=Path, required=True)
    collect.add_argument("--cache-dir", type=Path, required=True)
    collect.add_argument("--allow-network", action="store_true")
    collect.add_argument("--min-pages", type=int, default=50)
    collect.add_argument("--json", action="store_true")
    audit = sub.add_parser("audit-corpus", help="Validate locally stored snapshots (no network)")
    audit.add_argument("--snapshots", type=Path, required=True)
    audit.add_argument("--min-pages", type=int, default=50)
    audit.add_argument("--json", action="store_true")
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
        elif args.command == "research":
            result = research_provider(
                args.provider,
                cache_dir=args.cache_dir,
                live=args.allow_network,
                database=args.db,
            )
        elif args.command == "eval-real":
            result = evaluate_files(
                args.annotations, args.predictions, args.snapshots,
                resolutions_path=args.resolutions,
            )
        elif args.command == "perf":
            result = benchmark_offline(
                repetitions=args.repetitions,
                input_tokens=args.input_tokens,
                output_tokens=args.output_tokens,
                input_rate=args.input_rate,
                output_rate=args.output_rate,
            )
        elif args.command == "discover":
            result = discover_from_saved_html(args.base_url, args.html, args.out)
        elif args.command == "collect":
            result = collect_from_manifest(
                args.manifest, args.cache_dir,
                allow_network=args.allow_network, min_pages=args.min_pages,
            )
        elif args.command == "audit-corpus":
            result = audit_offline_dir(args.snapshots, min_pages=args.min_pages)
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
