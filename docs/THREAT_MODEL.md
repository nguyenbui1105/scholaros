# Threat model — v0.2 offline synthetic beta

| Surface | Risk | Current mitigation | Unresolved before real users |
| --- | --- | --- | --- |
| HTML ingestion | Prompt injection and hostile source text | HTML stripped; content treated as data; deterministic quote matching | Hostile redirect, parser fuzzing, robots/terms verification at scale |
| Source authority | Fake university/foundation claims | HTTPS/domain allowlist, snapshot hash, quote/value correspondence | Independent provider-domain and source-authenticity checks |
| Opportunity freshness | Stale dates, ambiguous cutoff time zones | Timestamp age and inclusive date semantics | Verify per-provider deadline timezone/cutoff |
| Student vault | Transcripts/visa/financial data disclosure | Explicit consent, Fernet option, no plaintext by default, purge API | Key rotation, per-user auth, secure backups, data retention/export/deletion |
| LLM adapter | Instruction injection and fabricated essays | Mock for tests, policy gates, literal evidence reviewer | Real adapter red-teaming, prompt privacy, semantic review |
| Ranking | False success probabilities | Explanations and explicit heuristic-only scoring | Held-out representative real outcomes and calibration |
| Forms | Unauthorized mass submission | Packet only; no portal runner | Portal terms, per-field permissions, exact signed approval and receipts |
| Dependencies | Known vulnerable packages | Python tests, type checking, lint; dependency auditing proposed | Enforced automated vulnerability/secret scanning |

## Assumptions
Only fictional fixtures are safe to use in the published demo. The optional online connector and real LLM adapter have not been tested with live sources. A domain suffix does not prove authority, and encrypted SQLite records are not production SaaS authorization.

## Required before hosted pilot
Threat-model review, third-party terms audit, scoped credentials, user consent ledger, encrypted backups, secure deletion and key rotation, per-tenant isolation, retention policy, incident procedure, monitoring, and explicit student approval before any external action.

**No legal, immigration or financial-aid advice; awards are never guaranteed.**
