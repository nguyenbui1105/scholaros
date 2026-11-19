# Implementation status — deterministic source ingestion phase

| Capability | Implementation | Tested? |
| --- | --- | --- |
| Typed eligibility reasons, conservative unknowns | `eligibility.py` | Yes |
| Claims and source allowlist | `models.py`, `config/` | Yes (not independently authenticated) |
| Pydantic provenance transport models | `records.py` | Yes |
| SQLite migrations, encrypted student vault, purge API | `storage.py` | Yes |
| PCC and Oregon Student Aid connector configurations | `ingestion.py` | Offline/permission gate only |
| Robots-aware opt-in fetch, URL restrictions and local cache | `ingestion.py` | Offline branches; live not tested |
| Deterministic quoted rule candidates | `ingestion.py` | Yes (synthetic fixture) |
| Source freshness and award deduplication | `ingestion.py` | Yes |
| Real source eligibility verification | **Not implemented** | No |
| LLM writing and application operations | Not implemented | No |
| Dashboard / hosted SaaS | Not implemented | No |
| Skills | 20 specifications, not all executable | No |

All fixture awards are fictional. CLI supports offline demo only at this stage. No real applicant PII should be used in this alpha.
