# Threat model (preproduction)

| Threat | Mitigation required before launch |
| --- | --- |
| Prompt injection in crawled scholarship pages | Treat web content as data; typed extraction, allowlists and model/tool separation |
| Fake official-looking scholarship sites | Verify authoritative provider domain and corroborate eligibility terms |
| Exposure of essays, transcripts or visa records | Encrypted per-user vault, scoped auth, least privilege, no PII in logs |
| Fabricated credentials in an AI draft | Claim-to-evidence checks and student confirmation |
| Violation of AI-use or portal terms | Per-provider policy versioning and fail-closed gates |
| Silent / duplicate submissions | Idempotency key, student confirmation, auditable transaction receipt |
| Race condition near deadlines | Source timestamps, time-zone-aware deadlines, human review |
| Misleading predicted success percentages | Prohibit probability UI without calibrated, externally validated model |
| Untrusted file uploads | File limits, content validation, isolated processing, malware scanning |
| Overbroad connector permissions | Least privilege, scoped tokens, revocation and expiry |

**Status:** controls above are design requirements; only basic policy/eligibility gates are in the reference package. Hosting real user data before the remainder is implemented is not approved.
