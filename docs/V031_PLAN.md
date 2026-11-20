# v0.3.1 Real-world evaluation — implementation plan

**Scope decision:** Real scholarship data cannot be honestly described as independently labeled without two independent human reviews and adjudication. Public search results are *candidates*, not validated pages; collecting even 50 URLs is not equivalent to retrieving 50 permitted live HTML snapshots. This milestone implements an auditable **50–100-page collection workflow**, separate human annotation protocols, abstention-aware metrics, and deterministic benchmarking. It does **not** fabricate a 50-page downloaded dataset or real-world accuracy scores.

## Gates (in order)

1. **Test first:** assert that candidate URLs cannot be promoted into permitted/validated source snapshots; labels without evidence or independent agreement are excluded; missing predictions count as abstentions; false eligible and uncertain decisions are reported explicitly.
2. **Collection:** accept official discovery seeds and extract links; canonical URL/domain checks; explicit robots.txt + terms/operator approval for network retrieval, no login/redirects; bounded 50–100 page collection with per-host delay, cached snapshots, immutable SHA-256; no network in CI.
3. **Annotation:** two reviewers independently label visa, school, GPA, deadline and major, citing exact snapshot excerpts for every known decision; an adjudicator resolves disagreement without seeing model predictions. Unreviewed stays UNKNOWN. Immutable snapshot IDs tie labels to source revisions. Preserve annotations separately from model outputs.
4. **Evaluation:** load reviewed gold and independently produced predictions from separate files; report eligible precision, recall, false-ELIGIBLE, UNKNOWN/NEEDS_VERIFICATION coverage, selective accuracy, confusion and sample counts; undefined denominators -> null, never 100%.
5. **Performance:** repeat an offline ingest → extract → match stage; report per-stage p50/p95 in milliseconds, run count and sequential throughput. LLM costs from observed token counts and explicit provider rates only; no guessed live pricing.
6. **Release:** test Ruff lint + format, mypy strict, pytest and >=85% coverage on Python 3.11/3.12; document actual verified numbers and missing collection/annotation work. Do not tag release if real-world goal unfulfilled.

## Data governance
- Public pages/quotes only, no student records. User must confirm source terms/license and robots permission before downloads.
- Store short evidence snippets and metadata, **not copyrighted full-page fixtures** in git without rights.
- No provider-specific F-1 eligibility assertion without a cited official, current individual-award rule.
- Do not infer source permissibility from robots.txt alone; site terms and explicit operator authorization remain a separate gate.
