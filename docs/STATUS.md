# Implementation status — correctness phase

| Capability | Status | Evidence |
| --- | --- | --- |
| Four-state eligibility with structured reasons | Implemented, CI validation pending | `eligibility.py` |
| Missing student values conservatively handled | Implemented, CI validation pending | `tests/test_eligibility.py` |
| Unicode/case/whitespace normalization | Implemented, CI validation pending | `eligibility.py` |
| Domain allowlist + malformed URL handling | Implemented (shape check only) | `config/official_domains.yaml` |
| Traceable international claim required | Implemented (claim is caller-supplied, not independently authenticated) | `models.py` |
| Offline fictional demo | Implemented | `__main__.py` |
| Actual scholarship ingestion/verified sources | Not implemented | `docs/UPGRADE_PLAN.md` |
| SQLite student vault, JSON schemas, real LLM | Not implemented | `docs/UPGRADE_PLAN.md` |
| Dashboard, live submission, SaaS | Not implemented | `docs/ROADMAP.md` |
| 20 skills | Specifications only | `skills/` |

**Deadline:** dates are inclusive: deadline == today does not expire. This does *not* establish the cutoff time zone. **Freshness:** verified age <= `freshness_days` is current; future-dated stamps are invalid. **Unknown rule:** no constraint is not affirmative unrestricted eligibility. **Authority:** accepted HTTPS domain suffixes are plausible, not independently authenticated. No real applicant PII supported.
