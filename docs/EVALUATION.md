# Evaluation plan

## Three audit lanes

**A. Eligibility / data integrity:** synthetic positives and hard negatives: F-1 restricted awards, citizenship clauses, graduate-only funding, GPA unknown, excluded majors, school restrictions, expired dates, stale source, absent official source, conflicting terms. Track false eligible / total ineligible as the primary safety metric.

**B. Narrative / AI policy:** blind review student-confirmed story claims vs generated text; score factual support, answer relevance, voice preservation, respect for provider AI rules and flagged ambiguous details. Record reviewer disagreement. Human-authored baseline required.

**C. Product / operations:** measure time spent per completed application, missed deadlines, rework, consent correctness, portal permissions, abandonment, feedback and actual outcomes. Never confuse winning with skill-generated rubric scores.

## Three-round self-audit protocol

1. **Architecture:** dependency edges, explicit non-goals, schema consistency, state transitions, idempotency.
2. **Safety & engineering:** unit tests, lint, negative controls, injection boundaries, private data minimization, policy fail-closed behavior.
3. **Developer experience:** quickstart reproducibility, repo discoverability, working links, accessibility and honest status communication.

Record observed outcomes and unresolved issues. Do not claim external CI passed until checks finish.
