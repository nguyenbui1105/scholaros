# Upgrade plan — v0.2 milestone

**Status:** Offline synthetic v0.2 implementation completed; live-source and production requirements explicitly deferred. Reviewed README, status, architecture, RFC, roadmap, existing Python core/tests, CI and all 20 skill specifications before modifying code.

## Strategy
Ship a **tested, offline, provenance-gated vertical slice** before extending integrations. Phase boundaries are release gates, not feature promises. No main-branch red builds deliberately accepted; every commit is CI-checked and repaired if necessary.

1. **Correctness (P1).** Replace the unsafe eligibility shortcut with typed claim records, conservative handling for missing student fields, normalized comparisons, source authority checks, reason codes and regression/property tests.
2. **Provenance & local data (P2).** Typed records and schemas, SQLite migration/storage, optional encrypted student vault and purge, synthetic examples.
3. **Ingestion (P3).** Two explicitly configured source adapters, robots-aware fetch interface, offline HTML fixtures, deterministic quote validation, freshness and deduplication. No browsing CI.
4. **Strategy and policy (P4).** Explainable, eligible-only ranking, portfolio optimization, fail-closed AI-use gates.
5. **Writing (P5).** Optional LLM interface with deterministic mock, evidence-supported outlines and independent unsupported-claim checks; no autonomous submission.
6. **CLI (P6).** Offline demo and a reproducible end-to-end command path with JSON output; dashboard is deferred until core is secure.
7. **Skills (P7).** Mark only executable/tested skill contracts as implemented; provide schema and verification in CI.
8. **Quality (P8).** Python 3.11/3.12 CI, Ruff, strict mypy, tests, benchmark, truthful README/status. Release/tag **only when gates pass**.

## Decision rules
- When official source usage/robots permission is uncertain, use committed fictional HTML fixtures rather than claim live scraping.
- A domain allowlist identifies possible authorities, not proof that a page is official.
- Same-day deadlines are inclusive by date because time zone/cutoff is unknown; a missing verified cutoff must be flagged for review before real submission.
- If any required student's value or official rule is missing, return NEEDS_VERIFICATION. Verified mismatches remain INELIGIBLE while returning all unknown reasons.
- No live PII or API keys in tests, repository or sample data.

## Verification gates
At each implementation phase: `pytest -q`, `ruff check .`, `ruff format --check .`, `mypy --strict src/`, package CLI smoke test; repair failures before claiming a phase completed. Use GitHub Actions as authoritative if local dependencies are unavailable.

## Known risk
Source authenticity, permission to fetch, AI-writing restrictions and student-data security require independent verification beyond synthetic fixtures. Until proven otherwise, classify as research beta **only for local synthetic data**, not as production-ready applicant SaaS.
