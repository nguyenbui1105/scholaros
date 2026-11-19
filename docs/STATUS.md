# ScholarOS status — offline synthetic beta

| Capability | Status | Verification |
| --- | --- | --- |
| Eligibility: four states, quote-backed constraints, normalization | Tested on synthetic cases | `test_eligibility.py`, benchmark |
| Provenance schemas and optional encrypted SQLite vault / purge | Tested | `test_records_storage.py` |
| PCC/OSAC connector definitions and opt-in, robots-aware fetch | Implemented, **live untested** | Offline tests only |
| HTML extraction, freshness, dedup | Tested on synthetic HTML | `test_ingestion.py` |
| Ranking + budget optimization | Tested on synthetic records | `test_ranking_policy.py`, `test_portfolio_writing.py` |
| Writing policy, MockLLM, literal review, outline and packet | Tested on fictional records | `test_portfolio_writing.py` |
| OpenAI real adapter | Implemented, **untested live** | Requires SDK and API key |
| Offline JSON CLI (`init`, `ingest`, `match`, `rank`, `explain`, `draft`, `review`, `packet`, `purge`, `demo`, `schemas`) | Tested | `test_cli_e2e.py` |
| 20 skill contracts | 9 limited tested, 11 specified | `test_skill_contracts.py` |
| Synthetic benchmark (36 pairs) | Test-asserted | `test_benchmark.py` |
| Real-world scholarship eligibility or confirmed provider AI policies | Not implemented | N/A |
| Live portal integrations / automatic submissions | Not implemented | N/A |
| Web dashboard / SaaS authentication | Not implemented | N/A |

**No legal, immigration or financial-aid advice.** Awards never guaranteed. Student data requires explicit consent, an encrypted vault key and additional security controls before real use; no production SaaS readiness claimed.

## Release quality gates
CI enforces Ruff lint/format, mypy --strict on src/, Python 3.11/3.12, pytest >=85% statement coverage, synthetic benchmark, and skill-contract validation. Dependency audit and Gitleaks are separately enforced. This document does not claim a hosted interface, or verified official-source eligibility.

## Verified release checklist (2026-11-18)
- Python 3.11 and 3.12: test matrix passing, Ruff lint and format, strict mypy.
- 76 tests, 92% statement coverage recorded before release formatting; final coverage minimum 85% is enforced by CI.
- 36 synthetic eligibility pairs with test-asserted zero false-ELIGIBLE; 10 literal unsupported claims detected in their toy benchmark.
- Gitleaks and dependency-audit jobs passed on the hardened build.
- A v0.2.0 release is intended only after CI passes for the release workflow commit.
