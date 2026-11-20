# v0.3.1 — observed offline benchmark (GitHub Actions)

**Run:** [CI 44699908310](https://github.com/nguyenbui1105/scholaros/actions/runs/44699908310), Python 3.12 runner, 100 repetitions per stage, synthetic source and student only.

| Stage | p50 | p95 | Mean |
| --- | ---: | ---: | ---: |
| HTML normalization (ingest) | 0.072038 ms | 0.079510 ms | 0.073313 ms |
| Deterministic candidate extraction | 0.022614 ms | 0.023696 ms | 0.023015 ms |
| Synthetic eligibility match | 0.405911 ms | 0.421234 ms | 0.411782 ms |

- Sequential throughput: **1,964.283 three-stage iterations/second** in a short warm-run sample, not guaranteed system throughput.
- Measured loop elapsed time: **0.050909 seconds**; this excludes process startup, network, storage, human review, real document acquisition and LLM inference.
- **Network calls: 0; LLM calls: 0; LLM cost: undefined (null).**
- Tests: **154 passing** (Python 3.12), statement coverage **85.49%**, Ruff lint/format and strict mypy passed. Independent security/dependency scan jobs also passed.
- Old synthetic 83-pair eligibility benchmark remains separate. **No independent real-world labels exist** in the repo. Thus real-source precision/recall, false-ELIGIBLE, abstention, and real API cost must be reported **unmeasured**.

The benchmark is single-process, synthetic-data, sequential microbenchmarking. Source snapshots are trusted fictional fixtures; timing results are NOT p95 for official scholarship sites, network calls, or production end-to-end flows. Rerun on representative hosts and real permitted sources before making a performance SLA.
