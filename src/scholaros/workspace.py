"""Encrypted local applicant workspace and deterministic specialist-agent orchestration.

ScholarOS assembles evidence-backed review packets. It has NO live submission
transport. Applicant approval binds a single packet hash and never transmits it.
"""

from __future__ import annotations

import json
import os
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .eligibility import assess_eligibility, normalize
from .models import AIUsePolicy, ClaimRecord, Decision, EligibilityResult, Opportunity, Student
from .policy import WritingMode, writing_mode
from .ranking import rank_eligible
from .records import EvidenceItem, StudentProfile
from .writing import story_to_outline


class ApplicantBundle(BaseModel):
    """Only applicant-confirmed evidence may be used for writing assistance."""

    model_config = ConfigDict(extra="forbid")
    student: StudentProfile
    evidence: list[EvidenceItem] = Field(default_factory=list)

    @field_validator("evidence")
    @classmethod
    def nonempty_ids(cls, evidence: list[EvidenceItem]) -> list[EvidenceItem]:
        if len({item.id for item in evidence}) != len(evidence):
            raise ValueError("Duplicate evidence item IDs")
        return evidence


class ScholarshipCase(BaseModel):
    """Manually reviewed per-award rule candidate; not trusted solely by its URL."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_url: str
    source_text: str
    verified_on: date
    reviewer_id: str | None = None
    eligible_levels: list[str] = Field(default_factory=list)
    eligible_visas: list[str] = Field(default_factory=list)
    eligible_majors: list[str] = Field(default_factory=list)
    allowed_schools: list[str] = Field(default_factory=list)
    min_gpa: float | None = None
    deadline: date | None = None
    rule_quotes: dict[str, str] = Field(default_factory=dict)
    international_quote: str | None = None
    ai_use_policy: AIUsePolicy = AIUsePolicy.UNKNOWN
    ai_policy_quote: str | None = None
    award_usd: int | None = None
    effort_hours: float | None = None
    other_requirements_reviewed: bool = False


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             default=str, separators=(",", ":")).encode("utf-8")).hexdigest()


def _cipher() -> Fernet:
    key = os.environ.get("SCHOLAROS_FERNET_KEY")
    if not key:
        raise RuntimeError("SCHOLAROS_FERNET_KEY is required for encrypted workspace files")
    return Fernet(key.encode("ascii"))


def save_private(path: Path, content: dict[str, Any]) -> None:
    """Encrypt with the user's environment key; never write plaintext to disk."""
    student = content.get("student")
    if isinstance(student, dict) and not student.get("consent_to_store", False):
        raise PermissionError("Explicit consent to store student profile is required")
    encrypted = _cipher().encrypt(json.dumps(content, default=str,
                                              ensure_ascii=False).encode("utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise PermissionError("Refuse to write through a symbolic link")
    flags = os.O_CREAT | os.O_TRUNC | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(encrypted)


def load_private(path: Path) -> dict[str, Any]:
    """Decrypt locally. Error if key is wrong; do not fall back to plaintext."""
    if path.is_symlink():
        raise PermissionError("Refuse to read workspace through a symbolic link")
    raw: Any = json.loads(_cipher().decrypt(path.read_bytes()).decode("utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Encrypted workspace must contain a JSON object")
    return raw


def _opportunity(case: ScholarshipCase) -> Opportunity:
    content_hash = sha256(case.source_text.encode("utf-8")).hexdigest()

    def claim(field: str, quote: str) -> ClaimRecord:
        return ClaimRecord(
            claim="F-1 eligible" if field == "international_claim" else field,
            source_url=case.source_url,
            retrieved_at=case.verified_on,
            quote=quote,
            content_hash=content_hash,
            verifier=case.reviewer_id or "",
        )

    return Opportunity(
        id=case.id,
        title=case.title,
        official_url=case.source_url,
        eligible_levels=case.eligible_levels,
        eligible_visas=case.eligible_visas,
        eligible_majors=case.eligible_majors,
        allowed_schools=case.allowed_schools,
        min_gpa=case.min_gpa,
        deadline=case.deadline,
        verified_on=case.verified_on,
        international_claim=(
            claim("international_claim", case.international_quote)
            if case.international_quote else None
        ),
        source_text=case.source_text,
        rule_claims={key: claim(key, value) for key, value in case.rule_quotes.items()},
        award_usd=case.award_usd,
        effort_hours=case.effort_hours,
        ai_use_policy=case.ai_use_policy,
        unknown_requirements=(
            () if case.other_requirements_reviewed else
            ("Other conditions have not been reviewed",)
        ),
    )


def _policy(case: ScholarshipCase) -> AIUsePolicy:
    """Do not trust catalog policy flags without source quote and human reviewer."""
    if case.ai_use_policy in (AIUsePolicy.PROHIBITED, AIUsePolicy.UNKNOWN):
        return case.ai_use_policy
    if not case.reviewer_id or not case.ai_policy_quote:
        return AIUsePolicy.UNKNOWN
    if case.ai_policy_quote not in case.source_text:
        return AIUsePolicy.UNKNOWN
    context = normalize(case.ai_policy_quote)
    if any(item in context for item in ("not allowed", "forbidden", "prohibited",
                                        "except", "excluding", "ineligible")):
        return AIUsePolicy.UNKNOWN
    if case.ai_use_policy is AIUsePolicy.ASSISTANCE_ALLOWED and (
        "ai-assisted drafting is permitted" in context or "ai tools allowed" in context
    ):
        return AIUsePolicy.ASSISTANCE_ALLOWED
    return AIUsePolicy.UNKNOWN


def create_workspace(
    applicant: ApplicantBundle,
    cases: list[ScholarshipCase],
    *,
    today: date,
) -> dict[str, Any]:
    """Execute six specialist roles, with review gates and zero external actions."""
    if not applicant.student.consent_to_store:
        raise PermissionError("Student consent to encrypted workspace is required")
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("Duplicate scholarship IDs are not allowed")
    if any(item.student_id != applicant.student.student_id for item in applicant.evidence):
        raise ValueError("Evidence belongs to a different student")
    student = Student(
        academic_level=applicant.student.academic_level,
        visa_status=applicant.student.visa_status,
        school=applicant.student.school,
        majors=applicant.student.majors,
        gpa=applicant.student.gpa,
    )
    events: list[dict[str, str]] = []
    packets: list[dict[str, Any]] = []
    eligible: list[tuple[Opportunity, EligibilityResult]] = []

    def event(agent: str, target: str, status: str) -> None:
        events.append({"agent": agent, "target": target, "status": status})

    confirmed = [item for item in applicant.evidence if item.confirmed_by_student]
    for case in cases:
        event("source_researcher", case.id, "catalog_case_reviewed" if case.reviewer_id
              else "source_review_required")
        opportunity = _opportunity(case)
        evaluation = assess_eligibility(student, opportunity, today=today)
        decision = evaluation.decision
        if not case.reviewer_id or not case.other_requirements_reviewed:
            if decision is Decision.ELIGIBLE:
                decision = Decision.NEEDS_VERIFICATION
        event("eligibility_guardian", case.id, decision.value)
        permission = _policy(case)
        mode = writing_mode(permission)
        event("ai_policy_officer", case.id, mode.value)
        outline: list[str] = []
        if decision is Decision.ELIGIBLE and mode in (
            WritingMode.FULL_DRAFT, WritingMode.OUTLINE_ONLY,
        ) and confirmed:
            outline = list(story_to_outline(
                "Explain how your evidence demonstrates your goals",
                confirmed, permission,
            ))
            event("narrative_coach", case.id, "evidence_only_outline")
        else:
            event("narrative_coach", case.id, "waiting_for_source_or_policy")
        if decision is Decision.ELIGIBLE:
            eligible.append((opportunity, evaluation))
        packet: dict[str, Any] = {
            "id": case.id,
            "title": case.title,
            "source_url": case.source_url,
            "source_reviewed_by": case.reviewer_id,
            "eligibility": decision.value,
            "reasons": [
                {"code": reason.code, "field": reason.field,
                 "severity": reason.severity.value}
                for reason in evaluation.reasons
            ],
            "essay_mode": "outline_only" if outline else "none",
            "outline": outline,
            "confirmed_evidence_ids": [item.id for item in confirmed],
            "required_checks": [
                "Confirm official source identity, dates and all eligibility clauses",
                "Review AI-use policy, disclosing AI use if required",
                "Applicant edits and approves every factual statement",
                "Upload required documents to the official provider portal",
                "Applicant explicitly approves the final exact packet and destination",
            ],
            "approved": False,
            "submission_status": "NOT_SUBMITTED",
        }
        packet["packet_hash"] = _digest(packet)
        packets.append(packet)
        event("packet_compiler", case.id, "review_packet_prepared")
        event("submission_coordinator", case.id, "blocked_pending_manual_submission")
    ranked = rank_eligible(student, eligible)
    event("strategy_ranker", "portfolio", "ranked_verified_only")
    return {
        "workflow": "assisted_application",
        "student_id": applicant.student.student_id,
        "created_for_date": today.isoformat(),
        "applications": packets,
        "ranked": [
            {"id": item.opportunity.id, "priority_score": item.score,
             "factors": list(item.reasons)}
            for item in ranked
        ],
        "audit_events": events,
        "external_submissions": 0,
        "note": "No provider submission integration is installed. Review and submit manually.",
    }


def approve_packet(
    workspace: dict[str, Any],
    packet_id: str,
    packet_hash: str,
    *,
    student_confirmed: bool,
) -> dict[str, Any]:
    """Approval of exactly one immutable packet; no transmission occurs."""
    if not student_confirmed:
        raise PermissionError("Student must explicitly confirm the exact packet")
    packets = workspace.get("applications", [])
    matched = [packet for packet in packets if packet.get("id") == packet_id]
    if len(matched) != 1:
        raise ValueError("No unique packet with this ID")
    packet = matched[0]
    if packet.get("packet_hash") != packet_hash:
        raise PermissionError("Packet digest mismatch: review latest packet before approval")
    # Exclude approval-related fields to ensure no edits have occurred after packet generation.
    core = {
        key: value for key, value in packet.items()
        if key not in {"packet_hash", "approved", "approval_packet_hash"}
    }
    core["approved"] = False
    if _digest(core) != packet_hash:
        raise PermissionError("Packet content changed after review")
    result = dict(packet)
    result["approved"] = True
    result["approval_packet_hash"] = packet_hash
    # No actual remote submit or fabricated receipt.
    result["submission_status"] = "NOT_SUBMITTED"
    return result
