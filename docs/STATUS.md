# Implementation status — offline end-to-end CLI phase

| Component | State | Evidence |
| --- | --- | --- |
| Four-state rule matching, snapshot quotes and missing data | Implemented/tested | `eligibility.py` |
| Provenance transport schemas | Implemented/tested | `records.py`, `scholaros schemas` |
| SQLite vault, opt-in Fernet and purge | Implemented/tested | `storage.py` |
| PCC + OSAC source connectors with opt-in robots check | Implemented, **live untested** | `ingestion.py` |
| Extract candidates, freshness, dedup | Implemented/tested on fixtures | `ingestion.py` |
| Ranking, effort optimizer, explanations | Implemented/tested | `ranking.py`, `portfolio.py` |
| AI-use gates and optional LLM interface | Implemented/tested with MockLLM only | `writing.py` |
| Literal evidence checker, rubric diagnostics, packet | Implemented/tested | `writing.py` |
| CLI: init, ingest, match, rank, explain, draft, review, packet, purge, demo, schemas | Implemented, CI pending | `__main__.py`, `workflow.py` |
| Genuine published scholarship matches | **Not provided** | Synthetic demo only |
| Live source eligibility provenance audit | **Not implemented** | Only fixture quotes checked |
| Dashboard, SaaS auth, autonomous submissions | **Not implemented** | Out of scope |
| 20 skills | Specifications only; not 20 executable agents | `skills/` |

**Scope:** Offline fixture explicitly labeled fictional. The pipeline demonstrates real stages, not a verified real-world scholarship outcome. No legal, immigration, or financial-aid advice; no award is guaranteed. Never use demo results as eligibility guidance.
