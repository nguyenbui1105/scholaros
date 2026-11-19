# Eligibility evaluation — adversarial synthetic benchmark

## Independent label set

The file `examples/benchmark_adversarial.csv` contains **83 labeled fictional student/opportunity pairs**. Expected outcomes were authored as fixed golden labels; they are **not calculated from the eligibility engine**. The original 36 cases remain in `examples/benchmark_36.csv` for comparison. Added adversarial labels cover finite/nonfinite and out-of-range GPA, malformed/bare hosts, negation and exclusions in eligibility quotes, visa and level aliases, named-month dates, and ambiguous numeric dates.

One fixed fictional opportunity/source snapshot is varied per case, with the date fixed to 2026-11-18. This controls time-dependent outcomes; it does not validate any actual published scholarship eligibility terms. Tests additionally cover malformed YAML, missing config, bare constraint strings, source hashes, property-based combinations, and the explicit-date policy.

## Blocking release thresholds

The benchmark CLI exits nonzero if **either** gate fails:

| Metric | Minimum |
| --- | --- |
| Number of independently labeled eligibility pairs | >= 60 |
| False-ELIGIBLE rate (FP / all non-eligible cases) | **exactly 0.0** |
| Unsupported-claim recall (flagged unsupported / all known unsupported) | **>= 0.95** |

The unsupported-claim probe uses 20 fictional unverified statements against one approved statement. It is a literal exact-match validator—not semantic fact verification. Unit tests also require 100% exact-state accuracy and eligible precision/recall on this intentionally restricted benchmark.

## Reproduce

```bash
pip install -e ".[dev]"
python -m scholaros.benchmark
pytest -q tests/test_benchmark.py tests/test_eligibility_regressions.py
```

## Limitations

Golden labels use a synthetic scenario and do not assess correctness against external sources. Quote-level negation detection is conservative and does not parse full legal clauses. GPA conversion across non-US scales, provider-local timezone discovery, real domain ownership confirmation, linguistic paraphrase entailment and real provider rule extraction remain out of scope. Do not extrapolate these scores to acceptance probability or provider eligibility.
