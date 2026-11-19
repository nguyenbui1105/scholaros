# ScholarOS v0.2.0 — Offline Synthetic Beta

A **reproducible, privacy-conscious developer beta** showing one end-to-end synthetic scholarship workflow. This release is **not a production scholarship eligibility service** and **not a deployed auto-application bot**.

## Working features

- Deterministic four-state eligibility with structured reasons, missing-data safeguards, normalized fields, and snapshot/quote/value checks.
- Pydantic records/provenance schemas; SQLite storage with opt-in Fernet encryption and logical student purge.
- HTML rule candidate extraction, source freshness/dedup, and two opt-in, robots-aware connector definitions (**live providers not yet verified**).
- Eligible-only ranking and time-budget optimization.
- Scholarship AI-use policy gates, deterministic MockLLM, optional untested real OpenAI adapter, evidence-only outline, literal claim reviewer, and **never-submitted** application packet.
- Offline JSON CLI (`scholaros demo --json`) and 20 skills: 9 with limited tested code, 11 specifications only.
- 36-pair labeled **synthetic** eligibility benchmark with zero false-ELIGIBLE assertions.

## Quality gates

CI checks Python 3.11/3.12, Ruff lint/format, `mypy --strict src/`, pytest with a minimum 85% coverage, synthetic evaluation, skill-status consistency, dependency audit and Gitleaks. See the workflow logs for the exact current test and coverage totals.

## Limitations

No real scholarship catalog, authoritative live-provider eligibility decisions, application submission, browser UI, hosted SaaS authentication, or award prediction. All example scholarships and applicants are **fictional**. A matching provider domain/quote is not independent verification of official program rules. Literal evidence matching can reject valid paraphrases. **No legal, immigration, or financial-aid advice; scholarship awards are never guaranteed.**

## Install

```bash
git clone https://github.com/nguyenbui1105/scholaros.git
cd scholaros
python -m pip install -e ".[dev]"
scholaros demo --json
python -m pytest -q
```

Read [STATUS](docs/STATUS.md), [EVALUATION](docs/EVALUATION.md), [SAFETY](docs/SAFETY.md) and [CHANGELOG](CHANGELOG.md) before evaluating or extending this beta.
