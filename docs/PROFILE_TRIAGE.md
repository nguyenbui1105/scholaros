# ScholarOS v0.7 — Preliminary profile matching with cited rules

This builds on [manual individual-award intake](SOURCE_INTAKE.md). **It is NOT a verified scholarship recommender or automatic application submitter**.

## Use the browser

1. Install `.[web]`, set your existing `SCHOLAROS_FERNET_KEY`, then run `scholaros web`.
2. Unlock localhost, complete **My profile** (visa, GPA etc.), and paste an individual scholarship page under **My researched awards**. Read the official site yourself; the app does not fetch the URL.
3. Open **Preliminary matching**. For the specific saved source revision, copy exact quotations for any clear **positive F-1 acceptance statement**, minimum GPA and deadline. Add your local reviewer label and confirm you actually checked the original.
4. Click **Save local rule review**. The encrypted review is stored in `.scholaros/source_reviews.enc`, bound to the imported page's URL, SHA-256 and award ID. If the source is edited/reimported as a new version, old assertions cannot silently apply to it.
5. See per-rule `preliminary_match`, `potential_mismatch` or `needs_verification` and a **potential_match/potential_mismatch/needs_verification** screening label.

**Every source still has final `eligibility: needs_verification`, `submission_status: NOT_SUBMITTED`.** A self-entered review is *not* an independent provider verification. Any preliminary match can be overturned by citizenship/residency, degree, school, enrollment, work authorization or other requirements that were missed or interpreted incorrectly.

## Guardrails

- Positive visa quote must directly mention F-1 and words such as "eligible", "may apply" or "open to"; whole-sentence negative/exclusion contexts are rejected.
- Minimum GPA and deadline must match literal values in an exact source excerpt, not only a form value.
- An invalid, modified or mismatched source hash/URL is rejected; no positive claim is inferred from an official-looking domain.
- Student missing GPA/visa remains unknown; below-minimum GPA produces only `potential_mismatch`, not conclusive ineligibility.
- Passing deadline may produce `potential_mismatch`; provider-local timezone is never silently assumed.
- Browser review POST requires authenticated local session, same-origin/CSRF and applicant acknowledgment. No LLM or external network is called by matching.
- The review form currently supports only F-1 positives, 0–4-scale GPA and ISO dates. A negative case, other visa types, PDF-only rules, time zone and complicated awards need human interpretation.

## Remaining requirements for a genuinely autonomous system

A permission-reviewed live award catalog, source authenticity checks and independent double annotation, complete scholarship-specific eligibility logic, student-authored/approved essays and documents, authorized per-provider submission adapters and verified provider receipts are still **not built**. Never treat the ranking of locally reviewed quotes as a verified eligibility result or an application.

Run offline tests with `pytest -q tests/test_profile_triage.py tests/test_triage_web.py`. Continuous integration also covers existing scholarship cases, encrypted workspace and security rules.

## Verified CI

The isolated feature-branch [CI 45086280411](https://github.com/nguyenbui1105/scholaros/actions/runs/45086280411) passed **210 automated tests** with **86.85% coverage** on Python 3.11, with Python 3.12, strict type checks, lint and security scan passing. These metrics measure code correctness on fictional test fixtures; they do **not** represent scholarship eligibility accuracy on real awards.
