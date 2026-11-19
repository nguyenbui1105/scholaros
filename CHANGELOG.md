# Changelog

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
