# Research annotation workspace (templates only)

**No real student cases, human reviewers, or source snapshots are bundled here.** Create `annotations.jsonl` and `predictions.jsonl` only after collecting permitted official-source snapshots and blinded expert reviews.

### Annotation record (schema illustration — NOT a verified review)

```json
{
  "case_id": "synthetic-only",
  "reviewer_id": "human-reviewer-a",
  "source_url": "https://example.edu/scholarship",
  "content_hash": "<SHA-256 of source text — replace>",
  "decision": "unknown",
  "field_labels": {
    "visa": "unknown",
    "school": "unknown",
    "gpa": "unknown",
    "deadline": "unknown",
    "major": "unknown"
  },
  "evidence_quotes": {},
  "other_requirements_reviewed": false,
  "annotated_at": "2026-11-19T00:00:00+00:00"
}
```

Source snapshots must be named `snapshots/<case_id>.json` in Pydantic `SourceSnapshot` format. Case IDs are opaque and should not contain names, SSNs, visa numbers, emails, etc.

`predictions.jsonl` contains independently generated model outputs:

```json
{"case_id":"synthetic-only","decision":"needs_verification"}
```

Only two **different** reviewer IDs with matching decisions and field annotations produce an adjudicated gold label; disagreements require a third reviewer in `--resolutions`. Do not fabricate or simulate human reviewers for field performance metrics.
