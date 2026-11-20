# ScholarOS v0.3.1 — Real-world evaluation framework

**Status: evaluation infrastructure implemented; the 50–100-page licensed/permission-reviewed real-world collection and independent annotation campaign is NOT yet complete. No real-world precision/recall can honestly be published.**

## 1. Candidate research sources

The repo includes [eleven initial public institutional source URLs](../examples/source_discovery_seeds.json) from ASU, PCC, OSAC, Berkeley, Michigan and UConn. These URLs were discoverable as public pages; that is **not** equivalent to reviewing download permissions, terms, individual-award eligibility or machine-readable reuse rights. OSAC's official catalog describes hundreds of awards, but one catalog URL remains **one source page**, not 600 independently crawled pages. Institutional summaries may not be the current authoritative sponsor rule; verify primary sponsor terms when possible.

## 2. Collection — 50–100 distinct pages, permission-gated

Discover same-origin scholarship detail links from a saved HTML index:

```bash
scholaros discover --base-url https://onsa.asu.edu/scholarships --html ./index.html --out ./candidates.json --json
```

The output manifest is **unapproved**. A human must check current provider terms, robots.txt, ownership of the source, authorized use, and edit the manifest's `approved_by_operator`, `terms_checked`, and individual candidate list. Approval must refer to the current website rules; robots permission alone does not confer rights.

After operator attestation and at least 50 approved candidate URLs:

```bash
scholaros collect --manifest ./approved-manifest.json --cache-dir .scholaros/eval-snapshots --min-pages 50 --allow-network --json
scholaros audit-corpus --snapshots .scholaros/eval-snapshots --min-pages 50 --json
```

Network use is opt-in. It checks HTTPS, domains, redirects, login/application exclusions, robots.txt, exact HTML content-type, response size, and rate limiting. It fails closed on retrieval uncertainty. Store the actual snapshots locally, **not in git**. Each has a timestamp and SHA-256; a hash does not authenticate the provider. Avoid scraping signed-in portals, CAPTCHAs or provider-restricted content.

The offline audit checks 50–100 unique snapshots; it reports **zero verified official pages and zero eligibility labels** until those separate human verification processes occur. The corpus may contain duplicates across different URLs; report distinct hashes separately.

## 3. Independent, blind gold annotation

For each student × scholarship pair, two independent human reviewers read the **same immutable source snapshot** and produce independent `Annotation` records. Annotate all five: `visa`, `school`, `gpa`, `deadline`, `major`; record one of `eligible`, `ineligible`, `unknown` and exact verbatim source excerpt for every known judgment. Also review other eligibility constraints, not only these five fields.

- A positive gold label needs all five fields affirmatively supported **and** a reviewer attestation that other eligibility requirements were reviewed.
- A negative gold label needs at least one explicitly verified exclusion with supporting quote.
- Unresolved eligibility remains UNKNOWN. Reviewers must not see model predictions.
- Disagreements and missing reviewers do **not** enter scored gold; require a distinct third reviewer/adjudicator.
- Source hashes and timestamps must match, or the record is rejected. Re-annotate when terms change.
- For F-1 scholarship decisions, a program-level webpage and an unqualified citizenship statement do not imply eligibility; seek an individual-award official rule and do not manufacture evidence.
- Do not retain real applicant PII; use fictional students for initial labels and explain this limitation.

Templates: [examples/evaluation](../examples/evaluation/README.md). Source license, reviewer names/roles and disputed cases belong in private project records, not public data.

## 4. Measure model decisions (gold and predictions are separate)

```bash
scholaros eval-real --annotations ./annotations.jsonl --predictions ./predictions.jsonl --snapshots ./snapshots --json
```

Metrics: `eligible_precision`, `eligible_recall`, `false_eligible_rate`, `false_eligible_count`, `coverage`, `abstention_rate`, `unknown_prediction_rate`, `needs_verification_rate`, `selective_accuracy` and confusion counts. Missing model predictions are abstentions. Zero denominators are JSON `null`, **not 100%**. Ineligible/unknown gold predicted ELIGIBLE is counted unsafe. Report sample counts and binomial uncertainty intervals once an adequate representative dataset exists.

**Model prediction export is not yet wired to real independently verified source-specific opportunities.** `eval-real` evaluates external predictions only, and must not be mistaken for a demonstrated end-to-end real-world scholarship matcher.

## 5. Offline stage performance (reproducible)

```bash
scholaros perf --repetitions 100 --json
```

Measured stages are **synthetic** HTML normalization, deterministic rule candidate extraction, and rule matching. Reports p50/p95/mean in milliseconds using nearest-rank percentiles, repetitions, sequential operations/sec, **0 network calls** and **0 LLM calls**. The command does not benchmark live HTTP latency, concurrent load, real LLM inference or entire student workflows.

LLM costs are `null` unless the operator supplies *observed* usage and explicit rates, e.g.:

```bash
scholaros perf --input-tokens 10000 --output-tokens 5000 --input-rate 2.0 --output-rate 8.0 --json
```

This is a **cost formula example**, not a live provider price quote or a recorded API call.

## 6. Release acceptance criteria

- Automated tests pass for independent adjudication, missing labels, hash/quote tampering, duplicate predictions, abstention/false-ELIGIBLE accounting, 60 **fictional** offline snapshots, no-network collection guards and timing/cost logic.
- Python 3.11/3.12 CI: Ruff lint/format, `mypy --strict`, coverage >=85%, dependency audit and Gitleaks.
- **Real-world dataset target:** >=50 independently permission-reviewed collected official pages, with distinct URLs and auditable retrieval dates; >=2 independent reviewers per scoring case; held-out eligible/ineligible/unknown distribution. **Not met until measured and reported with real source records.**
- Do not publish real-world performance scores until that target is met.

## Deferred research risk

Source terms and redistribution rights, changing award cycles, reviewer inter-rater agreement, difficult multi-clause language, unknown citizenship eligibility, applicant privacy, live API token usage, cold/warm cache differences, network p95 and throughput under load remain open.
