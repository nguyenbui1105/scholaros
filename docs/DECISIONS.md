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
