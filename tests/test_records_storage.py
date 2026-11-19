from datetime import datetime, timezone
from pathlib import Path

import pytest

from scholaros.records import (
    ClaimRecord, Opportunity, Requirement, SourceSnapshot, SourcedValue,
    StudentProfile, all_json_schemas,
)
from scholaros.storage import connect, load_student, purge_student, save_student


def sample_record() -> tuple[SourceSnapshot, Opportunity]:
    source = SourceSnapshot.from_text(
        "https://fixture.edu/award",
        "Example University Scholarship. F-1 eligible. Apply by 2027-06-01. $2000 award.",
        datetime(2026, 11, 18, tzinfo=timezone.utc),
    )
    def sourced(value: str, span: str) -> SourcedValue[str]:
        claim = ClaimRecord(
            claim=span, source_url=source.source_url, retrieved_at=source.retrieved_at,
            content_hash=source.content_hash, extracted_text_span=span, verifier="fixture",
        )
        return SourcedValue[str](value=value, provenance=claim)
    record = Opportunity(
        id="fixture-1",
        provider=sourced("Example University", "Example University"),
        title=sourced("Scholarship", "Scholarship"),
        deadline=sourced("2027-06-01", "2027-06-01"),
        requirements=(Requirement(field="visa", operator="in",
                                   expected=sourced("F-1", "F-1 eligible")),),
    )
    return source, record


def test_every_fact_must_match_snapshot() -> None:
    snapshot, opportunity = sample_record()
    assert opportunity.verify(snapshot)
    assert not opportunity.verify(SourceSnapshot.from_text(
        snapshot.source_url, "Changed page", snapshot.retrieved_at))


def test_all_models_have_schemas() -> None:
    assert len(all_json_schemas()) == 7


def test_no_plaintext_vault_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCHOLAROS_FERNET_KEY", raising=False)
    monkeypatch.delenv("SCHOLAROS_ALLOW_UNENCRYPTED_LOCAL", raising=False)
    with connect(tmp_path / "scholaros.db") as db:
        with pytest.raises(RuntimeError):
            save_student(db, StudentProfile(student_id="synthetic", consent_to_store=True))


def test_encrypted_vault_and_purge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from cryptography.fernet import Fernet
    monkeypatch.setenv("SCHOLAROS_FERNET_KEY", Fernet.generate_key().decode())
    with connect(tmp_path / "scholaros.db") as db:
        student = StudentProfile(student_id="synthetic", visa_status="F-1",
                                 consent_to_store=True)
        save_student(db, student)
        assert load_student(db, "synthetic") == student
        raw = db.execute("SELECT payload FROM student_vault").fetchone()[0]
        assert b"F-1" not in raw
        assert purge_student(db, "synthetic") == 1
        assert load_student(db, "synthetic") is None
