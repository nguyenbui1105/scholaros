# Changelog

## [Unreleased] — v0.5 local Student Experience MVP

- Added a real localhost-only browser UI using optional FastAPI/Uvicorn dependencies.
- Added ephemeral terminal-issued access code, SameSite=Strict HttpOnly session,
  Host and Origin/CSRF checks, CSP and HTML escaping.
- Added encrypted student profile entry, searchable institutional **unverified**
  source directory, deterministic demo agent workflow, application packet
  explanation and exact-hash student approval. Approval does **not** submit.
- Added offline TestClient regression tests for login guards, cross-origin
  requests, consent, XSS, PII encryption and non-submission.
- Real award catalog, independently verified applicant matches, hosted SaaS
  authentication and authorized provider submission are **not implemented**.
- Documentation: `docs/WEB_UI.md`, `docs/V05_PLAN.md`.


## [Unreleased] — encrypted assisted-application workspace

- Added interactive student onboarding to a Fernet-encrypted local workspace; no plaintext applicant storage or secrets in git.
- Added deterministic agent-role workflow for source triage, eligibility, AI policy, evidence-only narrative outline, packet compilation, ranking, and submission coordination.
- Added per-packet SHA-256 consent and no-submission guarantees with an explicit approval command.
- Added fictional sample catalog/profile and offline end-to-end CLI regression tests.
- No real scholarship catalog or provider-authorized automatic portal submission is included; a student's approval alone is not a submission receipt.
- Complete instructions: `docs/AGENT_WORKSPACE.md`.


## [Unreleased] — v0.3.1 real-source evaluation infrastructure

- Added same-origin scholarship URL discovery, exact HTTPS/host restrictions and operator-approved, robots-aware bounded collection.
- Added offline SHA-256 snapshot audit with deduplication and explicit separation of URLs, snapshots, and verified sources.
- Added independent two-reviewer evidence-linked annotations and third-party conflict adjudication without model predictions.
- Added metrics for eligible precision/recall, false-ELIGIBLE, abstentions, decision coverage, confusion counts and undefined denominators.
- Added measured offline ingest/extract/match p50/p95 timing and sequential throughput; optional estimated LLM costs require measured token usage and explicitly supplied prices.
- Added offline tests and CLI workflows. The 50–100 real licensed-page collection, blind human annotation campaign and real-world performance scores **are not yet delivered**.


## [Unreleased] — v0.3 source research slice

- Added `scholaros research pcc|osac` read-only CLI with offline cache and explicit `--allow-network` switch.
- Validate exact registry URL, SHA-256 snapshot integrity and freshness; preserve verbatim extracted candidate quotes and hash.
- Flag and suppress negated/exclusion contexts; return a manual review queue, `needs_verification`, zero verified individual awards and no ranking/submission.
- Optional persistence into the existing public-source SQLite table with no applicant data.
- Offline tests for both providers, cache miss, tampered snapshot, stale date, negated quote, CLI behavior and persistence. Live provider access remains unverified.

## [Unreleased] — eligibility hardening

- Added fail-closed 0–4 finite GPA validation, including NaN/Infinity/out-of-range guards.
- Unified source claim and requirement verification with negation/exclusion-aware sentence context, GPA-context numeric anchors and named-month date parsing.
- Normalized F-1/F1/f 1 and common undergraduate tokens; rejected bare string constraint collections.
- Replaced ad hoc domain file parsing with cached PyYAML safe_load, normalized case/leading-dot/IDNA allowlist, explicit missing-config errors, and rejection of bare-TLD hosts.
- Added explicit provider-local date policy and independently labeled 83-case adversarial benchmark with zero false-ELIGIBLE and >=95% unsupported-claim recall release gates.
- Regression and Hypothesis coverage for dangerous inputs; **112 passing tests** and **90.73% statement coverage** on GitHub Actions, with the 83-case synthetic benchmark meeting the explicit gates. No new live provider or submission claims.


## [0.2.0] — 2026-11-18

**Offline synthetic beta; not production scholarship advice.**

### Added
- Typed eligibility reasons, missing-value safeguards, Unicode normalization, quote/value-backed provenance screening.
- Pydantic opportunity and evidence transport models, JSON Schema exporter, SQLite migrations, opt-in Fernet vault and purge.
- Two real institutional source connector configurations, with opt-in robots-aware fetch but **no claim of live verification**.
- Deterministic HTML rule candidates, quote validation, freshness and deduplication.
- Eligible-only ranking, effort-budget optimizer, scholarship AI-use policy gates.
- LLM protocol, deterministic mock and optional real SDK adapter; evidence-only outlines, strict literal claim review, rubric/voice diagnostics, packet (never submitted).
- Offline JSON CLI, fictional fixture, 36 labeled synthetic benchmark, 20 versioned skill contracts and validator.
- GitHub Actions Python 3.11/3.12, Ruff, strict mypy, pytest coverage.

### Deliberately not shipped
Real scholarship catalog validation; claimed win-rate predictor; multi-user auth/dashboard; actual form submission; CAPTCHA handling; production PII processing. See [STATUS](docs/STATUS.md).

## [0.1.1] — 2026-11-18
Initial design-heavy research alpha and Python reference engine.
