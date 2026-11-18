# Skill catalog (20 specifications)

**Status:** These are skill **contracts**, not claims of 20 working agents. See [implementation status](../docs/STATUS.md).

| Group | Skill IDs |
| --- | --- |
| Student intelligence | `profile-ingestion`, `life-story-interviewer`, `achievement-extractor`, `evidence-verifier` |
| Scholarship research | `opportunity-discovery`, `eligibility-verification`, `source-freshness-check`, `scholarship-deduplication` |
| Strategy | `fit-ranking`, `effort-value-optimizer`, `narrative-angle-selector` |
| Writing | `story-to-outline`, `essay-coaching-and-drafting`, `voice-preservation`, `rubric-based-review` |
| Operations | `document-readiness`, `form-prefill`, `submission-readiness-check` |
| Evaluation | `outcome-tracking`, `experiment-analysis` |

## Universal contract

```json
{
  "input": {
    "task_id": "uuid",
    "student_id": "opaque-id-or-null",
    "inputs": {},
    "evidence_refs": [],
    "policy_context": {},
    "requested_at": "RFC3339 timestamp"
  },
  "output": {
    "status": "completed | needs_review | rejected | failed",
    "outputs": {},
    "evidence_refs": [],
    "uncertainties": [],
    "next_actions": [],
    "audit_refs": []
  }
}
```

Reject malformed input; propagate uncertainty; never forge evidence references or invent policy permissions. No skill may finalize a scholarship application without a student-confirmed checkpoint.
