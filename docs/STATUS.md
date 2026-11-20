# ScholarOS status — offline synthetic beta

| Capability | Status | Verification |
| --- | --- | --- |
| Eligibility: four states, quote-backed constraints, normalization | Tested on synthetic cases | `test_eligibility.py`, benchmark |
| Provenance schemas and optional encrypted SQLite vault / purge | Tested | `test_records_storage.py` |
| PCC/OSAC connector definitions and opt-in, robots-aware fetch | Implemented, **live untested** | Offline tests only |
| v0.3 read-only program-source research (candidates, hash, review queue, public SQLite snapshots) | Implemented; 13 offline research tests passing, live untested | `src/scholaros/research.py`, `tests/test_research.py` |
| HTML extraction, freshness, dedup | Tested on synthetic HTML | `test_ingestion.py` |
| Ranking + budget optimization | Tested on synthetic records | `test_ranking_policy.py`, `test_portfolio_writing.py` |
| Writing policy, MockLLM, literal review, outline and packet | Tested on fictional records | `test_portfolio_writing.py` |
| OpenAI real adapter | Implemented, **untested live** | Requires SDK and API key |
| Offline JSON CLI (`init`, `ingest`, `match`, `rank`, `explain`, `draft`, `review`, `packet`, `purge`, `demo`, `schemas`) | Tested | `test_cli_e2e.py` |
| 20 skill contracts | 9 limited tested, 11 specified | `test_skill_contracts.py` |
| Synthetic adversarial benchmark (83 pairs) | Test-asserted | `test_benchmark.py` |
| v0.3.1 source URL discovery and 50–100-page *permission-gated* collector | Implemented; network collection **not executed** | `collection.py`, `test_collector_v031.py` |
| Two-reviewer source-linked annotation and adjudicated metrics | Implemented; real labels **not collected** | `evaluation.py`, `test_evaluation_v031.py` |
| Ingest/extract/match offline p50/p95 and throughput CLI | Implemented; synthetic offline only | `performance.py`, `evaluation_cli.py`, `test_timing_v031.py` |
| LLM API cost measurement | Formula implemented for observed usage + operator-provided rates; live cost unmeasured | `performance.py` |
| 50–100 real official snapshots and blind double-reviewed cases | **Not completed / cannot claim measured accuracy** | `docs/V031_EVALUATION.md` |
| Real-world scholarship eligibility or confirmed provider AI policies | Not implemented; v0.3 never marks a program-level candidate eligible | N/A |
| Live portal integrations / automatic submissions | Not implemented | N/A |
| Local encrypted student onboarding and deterministic agent-role coordinator | Implemented, tested | `workspace.py`, `workspace_cli.py`, `tests/test_workspace*.py` |
| Verbatim-evidence outline and review packet with hash-bound consent | Implemented, tested on fictional cases | `workspace.py` |
| Real provider-approved submit adapters, receipt verification and portal automation | **Not implemented** | Explicitly blocked |
| Web dashboard / SaaS authentication | Not implemented | N/A |

**No legal, immigration or financial-aid advice.** Awards never guaranteed. Student data requires explicit consent, an encrypted vault key and additional security controls before real use; no production SaaS readiness claimed.

## Release quality gates
CI enforces Ruff lint/format, mypy --strict on src/, Python 3.11/3.12, pytest >=85% statement coverage, synthetic benchmark, and skill-contract validation. Dependency audit and Gitleaks are separately enforced. This document does not claim a hosted interface, or verified official-source eligibility.

## v0.3 source research verification (2026-11-20)
- Feature branch Python 3.11/3.12, strict mypy, Ruff lint+format, security scans and dependency audits passed.
- **125 tests passing**, **90.84% statement coverage** in [feature-branch CI](https://github.com/nguyenbui1105/scholaros/actions/runs/44696093675).
- Both source pages are **program-level landing pages**; zero verified individual awards and no automatic eligibility promotion.
- Live source fetching has not been tested or independently checked for providers' terms/robots; real student eligibility is not established.

## Verified release checklist (2026-11-18)
- Python 3.11 and 3.12: test matrix passing, Ruff lint and format, strict mypy.
- The eligibility hardening run passed **112 tests**, Ruff lint and format, and `mypy --strict src/` on both Python 3.11/3.12; measured statement coverage was **90.73%**.
- Hardening benchmark has **83 independently labeled fictional cases** (16 eligible positives; 67 others), **0 false-ELIGIBLE** and **20/20 literal unsupported claims detected**. Gate: zero false-ELIGIBLE and >=95% unsupported-claim recall. All figures are fixture-only.
- Gitleaks and dependency-audit jobs passed on the hardened build.
- v0.2.0 was released; subsequent hardening changes are unreleased until separately tagged.


## v0.3.1 status (unreleased evaluation infrastructure)
- 11 discovered official institutional source URLs are documented as **unreviewed candidates**, not 11 validated pages. No provider terms/robots permission is claimed.
- A bounded, opt-in 50–100-page local corpus collector and source audit exist; no such 50–100-page actual live corpus has been collected here. Do not quote synthetic fixture sizes as real.
- A human double-label and third-adjudicator pipeline enforces source SHA-256, verbatim evidence quotes and independent reviewer identities; **no real human labels exist in the repository**.
- Real-world precision, recall, false-ELIGIBLE rate, UNKNOWN/NEEDS_VERIFICATION rates, live p95 latency, throughput and API costs are therefore **unmeasured**, not 100%.
- Offline synthetic stage timing is available via `scholaros perf`; quantitative results should be reported with run/environment context after CI.
- The v0.2.0 release tag is unchanged; these are unreleased main/feature branch changes until independently accepted.

## v0.3.1 verified framework test (CI 44699908310)
- **154 passing automated tests**, **85.49% statement coverage** on the Python 3.12 runner.
- Python 3.11/3.12, Ruff lint/format, `mypy --strict`, dependency audit and Gitleaks pass.
- Offline synthetic benchmark p50/p95 and throughput are reported in [V031_BENCHMARK_RESULTS.md](V031_BENCHMARK_RESULTS.md).
- **0 verified live-page corpus files, 0 independent real human gold labels, 0 validated model-versus-real-source eligible predictions.** Therefore real-world metrics are **unmeasured**. This milestone delivers the evaluation framework, not completion of the human data campaign.

## Assisted-application workspace verification (2026-11-20)
- [CI feature branch](https://github.com/nguyenbui1105/scholaros/actions/runs/44727328577): **175 tests passed**, **86.54% statement coverage**, Python 3.11/3.12, Ruff lint/format, strict mypy, dependency audit and Gitleaks all passed.
- Live agent deployment: seven deterministic roles are orchestrated in-process, **not seven long-running LLM agents**. Real autonomous scholarship research and submission remain unimplemented.
- Encrypted onboarding, local reviewed-case matching, evidence-only outline, prefilled basic form fields, packet hash and explicit approval are available. CI fixture catalog is fictional; do not treat matches as real scholarship eligibility.
- The CLI has no authorized real-provider submission integration, and **no portal is contacted, no submission receipt is issued**.
