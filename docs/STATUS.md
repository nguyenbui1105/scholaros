# Implementation status — v0.1 research alpha

| Area | State | Evidence |
| --- | --- | --- |
| Python package + offline CLI | Implemented | `src/scholaros/__main__.py` |
| Conservative eligibility (coded gates) | Implemented, limited | `eligibility.py`, tests |
| Deterministic ranking of verified-eligible records | Implemented, heuristic | `ranking.py`, tests |
| AI writing/action policy gates | Implemented, limited | `policy.py`, tests |
| 20 skill contracts | Specified, not automated | `skills/*/SKILL.md` |
| Source crawling/official provider validation | Not implemented | RFC |
| Story interview and private vault | Not implemented | RFC |
| LLM writing assistants | Not implemented | RFC |
| Dashboard / database / authentication | Not implemented | roadmap |
| Browser prefill and submission integrations | Not implemented | roadmap |
| Real scholarship catalog or success prediction | Not provided | explicit scope |

**Important:** The reference model's `international_eligibility_confirmed` flag is a caller-provided assertion and is **not itself verified by the engine**. A production implementation must require independently auditable, official-source-backed claim records before setting it. HTTPS URL shape is not source authenticity.
