# Implementation status — provenance/storage phase

| Area | State | Evidence |
| --- | --- | --- |
| Four-state normalized eligibility + reason codes | Implemented/tested | `eligibility.py`, `test_eligibility.py` |
| Traceable source claim required | Implemented/tested, caller-authored claims | `models.py` |
| Pydantic provenance transport schemas + schema exporter | Implemented, CI pending | `records.py` |
| SQLite migration + student vault | Implemented, CI pending | `storage.py` |
| Fernet-encrypted student vault (opt-in) | Implemented, CI pending | `storage.py` |
| Student purge API | Implemented, CI pending | `storage.py` |
| Online ingestion/authoritative source verification | Not implemented | `docs/UPGRADE_PLAN.md` |
| Writing LLM adapter / application packet | Not implemented | `docs/UPGRADE_PLAN.md` |
| Dashboard / auth / hosted SaaS | Not implemented | `docs/ROADMAP.md` |
| 20 agent SKILL.md files | Specifications only | `skills/` |

**Important limitations:** Pydantic record schemas are separate from the reference eligibility dataclasses. Evidence/verifier strings are not proof of official policy. The vault refuses plaintext unless `SCHOLAROS_ALLOW_UNENCRYPTED_LOCAL=1`; encryption uses `SCHOLAROS_FERNET_KEY` and no keys are stored in git. SQLite `purge_student` removes logical records but does not guarantee secure deletion of copies, backups or filesystem blocks.
