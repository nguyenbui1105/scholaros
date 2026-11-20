"""Privacy-first applicant intake, local agent runs and exact-packet approval commands."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .records import EvidenceItem, StudentProfile
from .workspace import (
    ApplicantBundle,
    ScholarshipCase,
    approve_packet,
    create_workspace,
    load_private,
    save_private,
)


def interactive_intake() -> ApplicantBundle:
    """Minimal interactive student prompts. Secrets/visa numbers are never requested."""
    print("ScholarOS encrypted student intake. Do NOT enter passport or SSN numbers.")
    identifier = input("Choose a local profile ID (not your full name): ").strip()
    school = input("School: ").strip()
    visa = input("Visa category (e.g. F-1): ").strip()
    level = input("Academic level (e.g. undergraduate): ").strip()
    majors = input("Majors (comma separated): ").strip()
    gpa_raw = input("GPA on 0-4 scale (blank if unknown): ").strip()
    fact = input("One first-person statement you confirm as true (optional): ").strip()
    approved = input("Consent to encrypted local storage? Type YES: ").strip() == "YES"
    student = StudentProfile(
        student_id=identifier,
        school=school or None,
        visa_status=visa or None,
        academic_level=level or None,
        majors=tuple(item.strip() for item in majors.split(",") if item.strip()),
        gpa=float(gpa_raw) if gpa_raw else None,
        consent_to_store=approved,
    )
    evidence = (
        [
            EvidenceItem(
                id="student-statement-1",
                student_id=identifier,
                statement=fact,
                confirmed_by_student=True,
            )
        ]
        if fact
        else []
    )
    return ApplicantBundle(student=student, evidence=evidence)


def enroll(out: Path, *, profile_json: Path | None = None) -> dict[str, Any]:
    """Existing plaintext JSON input is allowed but never copied unencrypted."""
    if profile_json is None:
        bundle = interactive_intake()
    else:
        bundle = ApplicantBundle.model_validate_json(profile_json.read_text(encoding="utf-8"))
    if not bundle.student.consent_to_store:
        raise PermissionError("Please explicitly consent to encrypted local storage")
    save_private(out, bundle.model_dump(mode="json"))
    return {
        "saved_encrypted": True,
        "path": str(out),
        "evidence_items": len(bundle.evidence),
        "notice": "Remove any original plaintext profile JSON yourself after import",
    }


def execute(
    vault: Path,
    catalog_path: Path,
    out: Path,
    *,
    today: date,
) -> dict[str, Any]:
    bundle = ApplicantBundle.model_validate(load_private(vault))
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("opportunities"), list):
        raise ValueError("Catalog must be a JSON object with opportunities list")
    cases = [ScholarshipCase.model_validate(item) for item in raw["opportunities"]]
    workspace = create_workspace(bundle, cases, today=today)
    workspace["fixture_only"] = bool(raw.get("fixture_only", False))
    save_private(out, workspace)
    verified = sum(item["eligibility"] == "eligible" for item in workspace["applications"])
    need_review = sum(
        item["eligibility"] == "needs_verification" for item in workspace["applications"]
    )
    return {
        "workspace_encrypted": str(out),
        "fixture_only": workspace["fixture_only"],
        "opportunities_processed": len(cases),
        "eligible_screened": verified,
        "needs_verification": need_review,
        "packets_created": len(workspace["applications"]),
        "actual_submissions": 0,
        "note": "Review packets and manually submit on provider portal; no live submission adapter",
    }


def inspect(path: Path, *, reveal: bool = False) -> dict[str, Any]:
    workspace = load_private(path)
    if reveal:
        return workspace
    return {
        "applications": [
            {
                "id": item["id"],
                "eligibility": item["eligibility"],
                "submission_status": item["submission_status"],
                "packet_hash": item["packet_hash"],
                "approved": item["approved"],
            }
            for item in workspace.get("applications", [])
        ],
        "external_submissions": 0,
        "privacy": "Redacted summary; use --reveal to inspect all private packet details",
    }


def approve(
    path: Path,
    *,
    packet_id: str,
    packet_hash: str,
    student_confirmed: bool,
) -> dict[str, Any]:
    workspace = load_private(path)
    updated = approve_packet(workspace, packet_id, packet_hash, student_confirmed=student_confirmed)
    workspace["applications"] = [
        updated if item["id"] == packet_id else item for item in workspace["applications"]
    ]
    save_private(path, workspace)
    return {
        "packet_id": packet_id,
        "approved_for_manual_review": True,
        "submission_status": "NOT_SUBMITTED",
        "note": "No official portal was contacted; submit manually after verifying provider terms",
    }
