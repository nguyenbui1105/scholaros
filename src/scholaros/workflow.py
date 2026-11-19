"""Offline synthetic end-to-end pipeline; no scholarship assertions about real providers."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from .eligibility import assess_eligibility
from .ingestion import RuleCandidate, extract_candidates, html_to_text
from .models import AIUsePolicy, ClaimRecord, EligibilityResult, Opportunity, Student
from .ranking import rank_eligible
from .records import EvidenceItem, SourceSnapshot, StudentProfile
from .writing import MockLLM, application_packet, draft_assistance, review_claims

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "examples" / "synthetic_student.json"
HTML = ROOT / "examples" / "synthetic_scholarship.html"


def load_scenario(path: Path | None = None) -> dict[str, Any]:
    document = json.loads((path or SCENARIO).read_text(encoding="utf-8"))
    if document.get("_note", "").find("SYNTHETIC") < 0:
        raise ValueError("Offline demo only accepts a clearly marked SYNTHETIC scenario")
    return document


def build_synthetic(
    *, scenario_path: Path | None = None, html_path: Path | None = None,
    today: date | None = None,
) -> tuple[Student, Opportunity, EligibilityResult, list[RuleCandidate], list[EvidenceItem]]:
    """Raise if a required rule quote is absent; never infer an unrestricted rule."""
    info = load_scenario(scenario_path)
    raw = html_to_text((html_path or HTML).read_text(encoding="utf-8"))
    current = today or date.today()
    snapshot = SourceSnapshot.from_text(
        info["opportunity"]["official_url"], raw,
        datetime(current.year, current.month, current.day, tzinfo=UTC),
    )
    candidates = extract_candidates(snapshot)
    rules = {candidate.field: candidate for candidate in candidates}
    required = {"academic_level", "visa_status", "majors", "school", "min_gpa",
                "deadline", "international"}
    missing = required.difference(rules)
    if missing:
        raise ValueError(f"Fixture missing explicitly quoted rules: {sorted(missing)}")

    def claim(key: str, statement: str) -> ClaimRecord:
        candidate = rules[key]
        return ClaimRecord(
            statement, snapshot.source_url, current, candidate.quote,
            snapshot.content_hash, "deterministic-fixture-extractor",
        )

    person = StudentProfile.model_validate(info["student"])
    student = Student(
        academic_level=person.academic_level,
        visa_status=person.visa_status,
        majors=tuple(person.majors),
        school=person.school,
        gpa=person.gpa,
    )
    values = info["opportunity"]
    opportunity = Opportunity(
        id=values["id"], title=values["title"], official_url=snapshot.source_url,
        eligible_levels=[rules["academic_level"].value],
        eligible_visas=[rules["visa_status"].value],
        eligible_majors=[rules["majors"].value],
        allowed_schools=[rules["school"].value],
        min_gpa=float(rules["min_gpa"].value),
        deadline=date.fromisoformat(rules["deadline"].value),
        verified_on=current,
        international_claim=claim("international", "F-1 eligible"),
        source_text=snapshot.text,
        rule_claims={field: claim(
            "gpa" if field == "gpa" else field, field
        ) for field in ("academic_level", "visa_status", "majors", "school", "gpa", "deadline")},
        award_usd=values.get("award_usd"),
        effort_hours=values.get("effort_hours"),
        ai_use_policy=AIUsePolicy(values.get("ai_use_policy", "unknown")),
    )
    result = assess_eligibility(student, opportunity, today=current)
    evidence = [EvidenceItem.model_validate(item) for item in info["evidence"]]
    return student, opportunity, result, candidates, evidence


def run_stage(
    stage: str, *, scenario_path: Path | None = None,
    html_path: Path | None = None, opportunity_id: str | None = None,
    submitted_text: str | None = None,
) -> dict[str, Any]:
    student, opportunity, result, candidates, evidence = build_synthetic(
        scenario_path=scenario_path, html_path=html_path,
    )
    base: dict[str, Any] = {
        "fixture_only": True,
        "student_id": evidence[0].student_id,
        "opportunity_id": opportunity.id,
    }
    if opportunity_id is not None and opportunity_id != opportunity.id:
        raise ValueError(f"No fictional opportunity with id {opportunity_id!r}")
    if stage == "ingest":
        base["candidates"] = [asdict(item) for item in candidates]
    elif stage in {"match", "explain"}:
        base["decision"] = result.decision.value
        base["reasons"] = [asdict(item) for item in result.reasons]
    elif stage == "rank":
        base["ranked"] = [
            {"id": item.opportunity.id, "priority_score": item.score,
             "explanations": list(item.reasons)}
            for item in rank_eligible(student, [(opportunity, result)])
        ]
    elif stage == "draft":
        base["draft"] = draft_assistance(
            "Explain your learning journey", evidence,
            opportunity.ai_use_policy, MockLLM(),
        )
    elif stage == "review":
        text = submitted_text or "I practiced programming every day."
        report = review_claims(text, evidence)
        base["supported"] = list(report.supported)
        base["unsupported"] = list(report.unsupported)
    elif stage == "packet":
        draft = submitted_text or "I practiced programming every day."
        base["packet"] = application_packet(
            evidence[0].student_id, opportunity.id, draft, evidence, opportunity.ai_use_policy,
        )
    elif stage == "demo":
        base["decision"] = result.decision.value
        base["reasons"] = [asdict(item) for item in result.reasons]
        base["ranked"] = [
            {"id": item.opportunity.id, "score": item.score}
            for item in rank_eligible(student, [(opportunity, result)])
        ]
        base["draft"] = draft_assistance(
            "Explain your learning journey", evidence,
            opportunity.ai_use_policy, MockLLM(),
        )
        base["review"] = list(review_claims(base["draft"], evidence).unsupported)
        base["submission_status"] = "NOT_SUBMITTED"
    else:
        raise ValueError(f"Unknown workflow stage: {stage}")
    return base
