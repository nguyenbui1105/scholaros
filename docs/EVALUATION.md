# Evaluation — ScholarOS synthetic offline benchmark

## Protocol
The benchmark uses **36 labeled, fictional student/opportunity pairs** recorded in `examples/benchmark_36.csv`, run by `python -m scholaros.benchmark` and `tests/test_benchmark.py`. It contains:

- 6 eligible positive examples with alternate valid GPAs.
- 10 missing required student field cases (two per academic level, visa, major, school and GPA).
- 20 explicit mismatches (four per field).

Eligibility is compared against manually specified expected **four-state decisions**. A second audit uses ten **synthetic unsupported claims**, all distinct from the one confirmed evidence statement.

## Results (deterministic synthetic fixture only)
On the labeled fixtures, expected from the benchmark harness and asserted by the tests:

| Metric | Result |
| --- | ---: |
| Labeled pairs | 36 |
| Eligible precision | 1.000 (6 TP, 0 FP) |
| Eligible recall | 1.000 (6 TP, 0 FN) |
| False-ELIGIBLE rate | 0.000 (0 / 30 non-eligible) |
| Four-state exact accuracy | 1.000 (36 / 36) |
| Literal unsupported-claim detection | 1.000 (10 / 10) |

**These numbers are not independently measured performance on real scholarship providers or students.** The cases are intentionally simple and share one synthetic rule source; results are not generalizable. A real-world performance claim requires held-out institution-specific snapshots, manually checked rule provenance, adversarial extraction cases and blinded review.

## Failure and limitations
- Quote presence and metadata are not by themselves proof of source authenticity or correct interpretation.
- A literal reviewer will incorrectly reject some valid paraphrases and may miss complex unsupported implications.
- Current source fetching is opt-in and untested against real provider terms/robots; there is no production scholarship catalog.
- Priority scores are not award probabilities; no scholarship award outcomes have been measured.

## Reproduction
```bash
pip install -e ".[dev]"
python -m scholaros.benchmark
pytest -q tests/test_benchmark.py
```
