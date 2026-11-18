# Contributing to ScholarOS

ScholarOS welcomes responsible contributions that improve access and reliability.

1. Create an issue describing the problem, its proposed acceptance checks, and privacy implications.
2. Create a feature branch and keep changes narrowly scoped.
3. Use **synthetic** students and scholarships in fixtures; never upload private applicant data.
4. Run `python -m pip install -e ".[dev]"`, `ruff check src tests` and `pytest -q`.
5. Add tests for fail-closed eligibility, policy checks and negative/unknown paths.
6. For source discovery, include official-source URL, checked date, terms and provenance.
7. Open a PR using the template. Do not report AI-generated quality scores as acceptance probabilities.

## Agent skill changes
Each skill needs a versioned `SKILL.md` with input/output contract, guardrails, human checkpoint and failure tests. If code changes behavior, update the spec and regression tests in the same PR.

## Development priorities
See [ROADMAP](docs/ROADMAP.md). Accessibility, transparency and truthful communication take priority over automation volume.
