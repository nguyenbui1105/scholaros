# ScholarOS Skill Contracts — v0.2

**20 contracts; 9 with limited executable/tested functions; 11 specified only.** These are components, not 20 independently deployed agents.

| Skill | State | Evidence |
| --- | --- | --- |
| [`profile-ingestion`](profile-ingestion/SKILL.md) | specified | Contract only |
| [`life-story-interviewer`](life-story-interviewer/SKILL.md) | specified | Contract only |
| [`achievement-extractor`](achievement-extractor/SKILL.md) | specified | Contract only |
| [`evidence-verifier`](evidence-verifier/SKILL.md) | specified | Contract only |
| [`opportunity-discovery`](opportunity-discovery/SKILL.md) | specified | Contract only |
| [`eligibility-verification`](eligibility-verification/SKILL.md) | tested | `tests/test_eligibility.py` |
| [`source-freshness-check`](source-freshness-check/SKILL.md) | tested | `tests/test_ingestion.py` |
| [`scholarship-deduplication`](scholarship-deduplication/SKILL.md) | tested | `tests/test_ingestion.py` |
| [`fit-ranking`](fit-ranking/SKILL.md) | tested | `tests/test_ranking_policy.py` |
| [`effort-value-optimizer`](effort-value-optimizer/SKILL.md) | tested | `tests/test_portfolio_writing.py` |
| [`narrative-angle-selector`](narrative-angle-selector/SKILL.md) | specified | Contract only |
| [`story-to-outline`](story-to-outline/SKILL.md) | tested | `tests/test_portfolio_writing.py` |
| [`essay-coaching-and-drafting`](essay-coaching-and-drafting/SKILL.md) | tested | `tests/test_portfolio_writing.py` |
| [`voice-preservation`](voice-preservation/SKILL.md) | tested | `tests/test_portfolio_writing.py` |
| [`rubric-based-review`](rubric-based-review/SKILL.md) | tested | `tests/test_portfolio_writing.py` |
| [`document-readiness`](document-readiness/SKILL.md) | specified | Contract only |
| [`form-prefill`](form-prefill/SKILL.md) | specified | Contract only |
| [`submission-readiness-check`](submission-readiness-check/SKILL.md) | specified | Contract only |
| [`outcome-tracking`](outcome-tracking/SKILL.md) | specified | Contract only |
| [`experiment-analysis`](experiment-analysis/SKILL.md) | specified | Contract only |

## Universal envelope
See [docs/schemas/universal-envelope.schema.json](../docs/schemas/universal-envelope.schema.json). Source-record schemas can be exported with `scholaros schemas`.

**States:** `completed`, `needs_review`, `rejected`, `failed`. **Eligibility:** `eligible`, `ineligible`, `unknown`, `needs_verification`. Unknown input never grants eligibility or AI-writing permissions.

Run `python scripts/verify_skills.py` to ensure every `tested` or `implemented` label maps to a real implementation and test fixture. See [status](../docs/STATUS.md) for product-level limitations.
