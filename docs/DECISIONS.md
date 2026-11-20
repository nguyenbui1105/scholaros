# Product / engineering decisions

## D-001 — Sources
Two connector configurations represent real public pages: PCC Foundation Scholarship and Oregon Student Aid/OSAC. **These are real official institutions, but live robots permission and terms have NOT been independently confirmed.** Live requests are explicitly opt-in and robots-fail-closed. Synthetic HTML in `tests/fixtures` is not from these institutions and is never represented as a real award.

## D-002 — Domain trust
The `.edu`/`.gov` suffix allowlist is a triage signal, not a verified source authority chain. Eligibility claims must still be checked against an immutable snapshot and verified by a responsible reviewer.

## D-003 — Deadline
Date-only deadlines are inclusive through the date but do **not** imply local time, portal cutoff, or ability to submit at 11:59. Until verified, keep a manual deadline warning.

## D-004 — AI writing
Unknown scholarship policies must fail closed. No writing generation is permitted solely because a user wants it.

## D-005 — Vault
Fernet is enabled by supplying a key; plaintext requires an explicitly named local-only override. Secure deletion of WAL/backups/disks is not guaranteed by SQL DELETE.

## D-006 — Product scope
The beta vertical slice uses synthetic fixtures. No portal login, CAPTCHA bypass, unattended application submissions, or AI-generated success probabilities.

## D-007 — Explicit evaluation date and timezone (2026-11-18)
`assess_eligibility(..., today=...)` **requires a plain `datetime.date`** from the scholarship provider's local calendar date, as resolved by its verified published timezone/cutoff; it does not calculate a timezone automatically, use local machine time, or accept a `datetime` object. Calendar-date deadlines are inclusive for conservative *screening* only. If provider timezone or cutoff is unknown, the application requires human review before submission. The demo/benchmark fixes an artificial evaluation date; it must not be used to infer current live deadline status. Numeric slash dates (e.g. 03/01/2025) are ambiguous and deliberately not verified; ISO `YYYY-MM-DD` and named-month textual dates are accepted if unambiguous.

## D-008 — GPA scale and conservative source language
The reference evaluator supports only finite GPA values on a **0.0–4.0 scale**. No other scale can be inferred from a number; unsupported scales require explicit normalization with verified school policy in a future model. Invalid GPA returns `NEEDS_VERIFICATION` (the model's structured unknown state), never a positive result; any other independently verified hard mismatch remains a hard failure. Source quote validation rejects nearby negation/exclusion terms; regex screening is not sufficient legal/policy interpretation, so complex clauses require human review. Only `https` hosts with at least two labels are accepted, and a configured normalized YAML allowlist is mandatory; the allowlist is not proof of provider authority.

## D-009 — v0.3 program-level discovery safety (2026-11-19)
The two configured public pages [PCC Foundation scholarships](https://www.pcc.edu/enroll/paying-for-college/scholarships/apply/) and [OSAC Scholarship Application](https://www.oregonstudentaid.gov/scholarships/osac-scholarship-application/) are *application program landing pages*. A program page does not constitute individual scholarship criteria, international/F-1 permission, AI-use terms, or award-specific deadlines. A quote match does not promote source content to eligible. Source research returns `needs_verification` for both providers, `verified_awards=0` and an explicit review queue. Cache content is **never trusted merely because its hash is internally consistent**. Network access is opt-in, subject to robots.txt and normal provider terms. The documented URLs were checked by public search; actual production fetch permissions and published details must be revalidated by the operator.
