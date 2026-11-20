# Assisted-application workspace — engineering plan

Goal: install ScholarOS, enter the student's *verified* facts once, then automatically coordinate source review, eligibility triage, ranking, narrative coaching (only when provider rules permit), packet compilation and a human approval queue.

**Safety boundary:** scholarship portal submission is an external side effect and cannot be safely generalized across unrelated websites. An approval for one packet and an explicit, independently permission-checked provider adapter are required per submission. No adapter currently has an authorized real portal integration; the initial shipped workflow therefore stops at a ready-for-human-review packet. It must never claim a successful submission.

## Implementation phases
1. Test-first deterministic roles + evidence-based processing. Missing official award rules => needs_verification, no invented facts; negative eligibility quote cannot become eligible.
2. Interactive minimal profile intake to an encrypted Fernet file, key only from environment. No plaintext persistence and no student PII logged to CI.
3. Agent execution via a local catalog of scholarship *cases with official source snapshots and documented reviewer attestation*. Apply existing eligibility engine, explicit AI policy gates, evidence-based outlines, packet hashes and audit trail. Unknown policy blocks writing. All packets begin NOT_SUBMITTED.
4. Intent-bound approval records with exact packet digest; approval alone does not submit and can be invalidated by changes. No credentials or provider API requests.
5. CLI and comprehensive offline e2e tests. Ruff, mypy strict and Python 3.11/3.12 CI; update honest status and docs.

## Deferred prerequisites for real autonomous completion
- Primary-source individual-award catalog with reviewed restrictions for F-1 students
- Verified scholarship-specific AI-use permissions and human-reviewed essays
- Provider-specific, officially permitted API integration with authorization, rate limits, audit receipts, retry/idempotency and consent per exact packet
- Student-friendly authenticated UI, key rotation, sensitive document processing and operational monitoring

This is a usable **assisted-application local MVP**, not a bot that can submit to arbitrary portals.
