# v0.6 — Import individual scholarship pages into the encrypted research queue

## What you can do

1. Start the [local student dashboard](WEB_UI.md) with `scholaros web`.
2. Unlock using the terminal code. Open **My researched awards**.
3. Open the official page for a **specific scholarship**, confirm you are allowed to use the published content, and paste the URL, individual award title and relevant page text.
4. ScholarOS stores the copied text **encrypted** in `.scholaros/source_awards.enc` (with the same `SCHOLAROS_FERNET_KEY` as your student profile).
5. The dashboard displays a searchable list of imported award pages, SHA-256 source digest, literal candidate quotes and a **human review checklist**.

**No URL is automatically fetched.** No third-party page is copied into the repository or sent to an LLM. All imported award snapshots remain `NEEDS_VERIFICATION` and `NOT_SUBMITTED`.

## Why the manual evidence step exists

The university-domain screen only checks whether an HTTPS URL is plausible; it cannot guarantee that the institution created the page. Likewise, a sentence saying *F-1 students may apply* may have exceptions elsewhere in the page; it is not a complete admissibility or immigration decision. Applicant-pasted text is untrusted and may omit essential requirements.

The deterministic extractor finds a narrow subset of literal wording (not a general document understanding model). Text in explicitly negated or excluded contexts is suppressed rather than asserted as a positive condition. A positive-looking excerpt never becomes a verified provider rule without independent human review. Some true rules will remain undetected.

## Versioning and privacy

- Entries are deduplicated by exact URL and hash of normalized page text. New text creates a second historical version rather than overwriting the old.
- The local source file is encrypted using your Fernet key. Do not lose or publish the key. Backups, key rotation, multi-user access controls and secure deletion are not yet implemented.
- No passport data, bank numbers, recommendation letters, application passwords or immigration documents should be pasted into the source field.
- Browser forms are protected by existing local access-code login, CSRF/Origin checks, and output HTML escaping. Do not expose the service through tunnels or reverse proxies.
- No `ELIGIBLE`, `SUBMITTED` or provider receipt is created by this feature.
- Existing **Run agents (demo)** still uses a fictional local catalog. Imported award pages are intentionally not converted into fictional verified-award rules.

## Next engineering milestones

1. Obtain permission for current individual-award page acquisition, with bounded, source-specific connectors.
2. Implement a human verification workflow covering international/F-1 status, citizenship, residency, school, major, GPA, academic level, award amount, deadline and timezone; independent evidence provenance.
3. Only then connect human-reviewed per-award rules to student-profile matching, application-specific essay requirements, packet editing, explicit consent and supported submission adapters.
4. Record actual provider submission receipts when authorized rather than marking applications successful from local approvals.

See [implementation status](STATUS.md) and [evaluation design](V031_EVALUATION.md). No real-world performance or scholarship application success rates are claimed.
