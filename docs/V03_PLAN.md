# v0.3 — Grounded source research (narrow verified scope)

## Decision and safety boundary

Existing PCC Foundation and Oregon Student Aid OSAC source URLs were checked against public institutional pages on November 19, 2026. These pages describe **application programs**, not a normalized, verified individual award catalog. Do **not** infer blanket F-1 eligibility, award amount, scholarship-specific AI use permissions, or individual deadlines from a program landing page.

## Implementation plan

1. Introduce a read-only source research pipeline that consumes a **live opt-in robots-aware fetch** or locally cached snapshot. Validate exact registry URL, snapshot SHA-256, UTC timestamp and freshness before extracting candidate rule quotes.
2. Separate ***extracted candidate*** from ***verified eligibility***. Recheck quote presence, suppress explicitly negated/exclusion contexts and return an audit-ready manual review queue with every source link and hash. Default result: `needs_verification`; **no automatically eligible scholarships**.
3. Persist public source snapshots in existing SQLite `public_snapshots` table only. Do not collect applicant PII or auto-submit.
4. Expose a CLI `scholaros research pcc|osac` with explicit `--allow-network`; offline requires cache and never performs a network request. JSON remains stable.
5. Test both built-in providers using synthetic stored snapshots, tampered hashes, mismatched URLs, stale dates, negated quoted evidence and offline cache miss. CI must remain green on 3.11/3.12 with strict typing and >=85% coverage.

## Intentionally deferred

No crawler for 600 OSAC scholarship descriptions, no authenticated portals, no real-student F-1 eligibility assertions, and no ranking from unreviewed source candidates. An application program page is not the same as an individual scholarship. Historical emails from failed CI runs are not new repository errors.

## Ship criteria

Ruff lint+format, mypy --strict, pytest coverage, synthetic benchmark, secret scan and dependency audit all pass on feature branch and the fast-forwarded main commit. Update STATUS, README, DECISIONS and ROADMAP with precise scope.

Implementation: see `src/scholaros/research.py`, `tests/test_research.py` and `docs/RESEARCH_V03.md`. CI passed on the feature branch: 125 tests, 90.84% coverage, Python 3.11/3.12, Ruff, strict mypy, pip-audit and Gitleaks. See https://github.com/nguyenbui1105/scholaros/actions/runs/44696093675. Live provider permission is not independently established.
