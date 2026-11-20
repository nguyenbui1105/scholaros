# ScholarOS v0.3 — program-source research

**Status: offline-tested developer feature; not live scholarship eligibility advice.**

## Source registry (checked November 19, 2026)
- **PCC Foundation scholarships:** https://www.pcc.edu/enroll/paying-for-college/scholarships/apply/
- **Oregon Student Aid / OSAC:** https://www.oregonstudentaid.gov/scholarships/osac-scholarship-application/

These are official institutional *program application pages*. OSAC describes an application that includes hundreds of scholarships; each individual scholarship may have different residency, citizenship, level, campus, need and AI-writing requirements. **Do not promote an F-1 student to eligible from either program page alone.**

## Commands
```bash
pip install -e ".[dev]"
scholaros research pcc --allow-network --cache-dir .scholaros/cache --json
scholaros research pcc --cache-dir .scholaros/cache --json
scholaros research osac --allow-network --cache-dir .scholaros/cache --json
scholaros research pcc --cache-dir .scholaros/cache --db .scholaros/research.db --json
```

`--allow-network` is the only way the research CLI initiates a new remote fetch. Fetching is restricted to the built-in registry, only HTTPS, with a User-Agent, robots.txt check, no redirects, limits on response size and minimum delay. Site terms and page suitability should be independently confirmed. Live requests may be denied by robots.txt or a provider; that is expected fail-closed behavior. Offline mode requires a prior local cache snapshot and **never fetches**.

## Fields and trust semantics
- `source_url` is compared to the exact registry URL.
- `content_hash` is the SHA-256 of stored text. The hash detects accidental or adversarial text changes but **does not prove who authored the page**.
- `retrieved_at` records a timezone-aware timestamp; stale or future-dated snapshots yield no candidates.
- Each `candidate` includes a verbatim quote, exact source URL, snapshot hash and `status=unverified`. A negative/excluded context is suppressed.
- `review_reasons` explicitly flags unverified *individual* requirements, F-1/citizenship, AI-use rules, award-specific deadlines and timezones.
- `decision=needs_verification`, `verified_awards=0`, `ranked=[]`, `submission_status=NOT_SUBMITTED` regardless of a positive-looking program page. No standalone program page can change this.
- Optional SQLite storage inserts **public snapshots only**; no student profile, visa documents or personal narrative is stored.

## Test strategy and deferred scope
Synthetic cached examples exercise both built-in providers, digest tampering, unknown source URL, stale dates, negated/exclusion text, default offline cache miss, SQLite persistence and CLI behavior. No live network in CI.

Not yet implemented: crawling specific awards from catalogs, authenticated systems, per-award manual attestation records, verified F-1 matching, trusted eligibility ranking from official providers, secure hosted dashboard or submission. These must be handled as separate milestones with source/adjudication benchmarks.
