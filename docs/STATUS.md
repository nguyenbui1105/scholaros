# Implementation status — policy/essay reference phase

| Component | State | Evidence |
| --- | --- | --- |
| Conservative structured eligibility + snapshot quotes | Implemented/tested | `eligibility.py` |
| Provenance schemas and encrypted SQLite vault | Implemented/tested | `records.py`, `storage.py` |
| Two official source connectors, opt-in robots-aware fetch | Implemented, **live untested** | `ingestion.py` |
| HTML quoted extraction, freshness and dedup | Implemented/tested on synthetic HTML | `ingestion.py` |
| Eligible-only ranking and score factors | Implemented/tested | `ranking.py` |
| Effort-budget optimization | Implemented, CI pending | `portfolio.py` |
| AI writing modes and submission gates | Implemented, CI pending | `policy.py` |
| LLMClient + MockLLM, optional OpenAI SDK | Implemented, CI pending (real adapter untested) | `writing.py` |
| Outline, literal claim audit, voice/rubric diagnostics | Implemented, CI pending | `writing.py` |
| Application-ready packet (not submission) | Implemented, CI pending | `writing.py` |
| Command-line end-to-end pipeline | Not implemented yet | `docs/UPGRADE_PLAN.md` |
| Dashboard/auth/production data handling | Not implemented | `docs/ROADMAP.md` |
| 20 agent skills | Specifications only | `skills/` |

**Important:** Evidence audit is deliberately literal and will flag supported paraphrases; it is NOT semantic entailment checking. The OpenAI adapter is optional and untested without credentials; the deterministic mock is for offline tests. No writing feature bypasses scholarship AI-use policies, and no application is submitted by ScholarOS.
