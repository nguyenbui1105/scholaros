# ScholarOS roadmap

## v0.2 — offline synthetic beta (implemented)
- [x] Conservative structured eligibility, source quote/value checks and normalized comparison
- [x] Provenance transport schemas and local SQLite+Fernet vault with purge
- [x] Two source connector configurations; opt-in robots checks, snapshots and deterministic parser
- [x] Freshness, deduplication, priority ranking and effort-budget optimizer
- [x] Writing policy gates, MockLLM, outline, literal claim audit and packet
- [x] Offline JSON CLI and fictional end-to-end fixture
- [x] 20 skill contracts with explicit status and automated contract validator
- [x] 83-pair synthetic adversarial benchmark, Python 3.11/3.12 lint, strict typing and tests

## v0.3 — read-only source research (feature branch)

- [x] Exact PCC/OSAC provider registry with read-only program-page snapshot inspection
- [x] Snapshot URL/digest/freshness checks and verbatim candidate excerpts
- [x] Suppression of excerpted candidates in explicitly negated/exclusion contexts
- [x] Offline-cache CLI and optional public snapshot storage without applicant PII
- [x] Manual review queue, no automatic eligible rankings, no submission
- [ ] Real permission/robots validation end-to-end for current live websites
- [ ] Individual award catalog, per-award authoritative rule adjudication

## v0.3.1 — independent evaluation tooling (implemented; real-world study pending)
- [x] Public candidate URL registry (11 discoverable institutional URLs, not validated snapshots)
- [x] Permission-gated 50–100-page bounded collector and offline SHA-256 audit
- [x] Two-reviewer evidence-anchored annotation model and conflict-safe adjudication
- [x] Metrics with abstentions and null when real-world labels are missing
- [x] Offline stage p50/p95, throughput, explicit-cost calculator
- [ ] Collect >=50 distinct, terms/robots-checked official pages and document permitted reuse
- [ ] Two blinded independent reviewers per scored case and adjudication for conflicts
- [ ] Run held-out real-source matching accuracy and report confidence intervals
- [ ] Measure live network and LLM latency/throughput/cost using actual usage

## Assisted-application local MVP (implementation underway)

- [x] Encrypted one-time applicant intake and local profile workspace
- [x] Seven deterministic agent roles with source and AI-policy gates
- [x] Evidence-only story outline and hash-bound packet approval queue
- [ ] Verified catalog of individual real scholarships accepting relevant applicant profiles
- [ ] Audited, officially permitted provider API submission adapters and receipts
- [ ] Authenticated web UI, applicant document vault and granular consent ledger

**No unattended form submission or CAPTCHA circumvention is planned.** After reviewing a packet, the applicant must explicitly authorize its exact destination and final version.

## v0.5 — local Student Experience (preview)

- [x] Localhost browser UI with authenticated access-code session
- [x] Encrypted student onboarding and saved profile editing
- [x] Searchable directory of unverified institutional scholarship sources
- [x] Deterministic agent demonstration and reviewable packets
- [x] Explicit SHA-256-bound approval, no external submission
- [x] Local browser security controls and offline tests
- [ ] Current, independently verified per-award catalog relevant to F-1 students
- [ ] Student-friendly real scholarship eligibility search, including provider-local deadlines
- [ ] Full essay editing and independent human factual review
- [ ] Officially permitted provider submission integration and receipt verification
- [ ] Authenticated hosted application, secure backup/key rotation and security audit

See [web UI guide](WEB_UI.md) and [implementation plan](V05_PLAN.md).
**Local browser does not mean production SaaS readiness.**

## Next — grounded public-source beta
- [ ] Independent real-source authority/permission validation and repeatable robots compliance
- [ ] Manually adjudicated eligibility cases from multiple providers (F-1, citizenship, enrollment conditions)
- [ ] Provider-specific AI-use policy evidence and versioning
- [ ] Robust extraction for complex dates, rule conditions and conflicts; never promote ambiguous rules
- [ ] Authentication, multi-user consent, encryption key rotation and auditable evidence vault
- [ ] Blinded essay review, semantic claim checking with human review, multilingual accessibility
- [ ] Secure, student-approved form preparation; no unattended submission
- [ ] Accessible dashboard after threat-model review and controlled student pilot

## Release blockers for production
No real-world rule benchmark, portal terms validation, user data protection certification, authentication, or independent security assessment exists. **ScholarOS v0.2 must not be marketed as live scholarship eligibility advice.**
