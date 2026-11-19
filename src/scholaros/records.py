"""Validated provenance-first transport schemas. All opportunity assertions are sourced."""
from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class StrictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceSnapshot(StrictRecord):
    source_url: str
    retrieved_at: datetime
    content_hash: str = Field(min_length=64, max_length=64)
    text: str

    @field_validator("retrieved_at")
    @classmethod
    def timezone_required(cls, timestamp: datetime) -> datetime:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("retrieved_at must have a timezone")
        return timestamp

    @classmethod
    def from_text(cls, source_url: str, text: str, retrieved_at: datetime | None = None
                  ) -> SourceSnapshot:
        timestamp = retrieved_at or datetime.now(UTC)
        return cls(source_url=source_url, text=text, retrieved_at=timestamp,
                   content_hash=sha256(text.encode("utf-8")).hexdigest())


class ClaimRecord(StrictRecord):
    claim: str
    source_url: str
    retrieved_at: datetime
    content_hash: str = Field(min_length=64, max_length=64)
    extracted_text_span: str = Field(min_length=1)
    verifier: str

    def verifies(self, snapshot: SourceSnapshot) -> bool:
        return (
            self.source_url == snapshot.source_url
            and self.content_hash == snapshot.content_hash
            and self.retrieved_at == snapshot.retrieved_at
            and bool(self.verifier.strip())
            and self.extracted_text_span in snapshot.text
        )


class SourcedValue(StrictRecord, Generic[T]):
    value: T
    provenance: ClaimRecord


class Requirement(StrictRecord):
    field: str
    operator: str
    expected: SourcedValue[Any]


class Opportunity(StrictRecord):
    id: str
    provider: SourcedValue[str]
    title: SourcedValue[str]
    deadline: SourcedValue[str] | None = None
    requirements: tuple[Requirement, ...] = ()
    award_usd: SourcedValue[int] | None = None
    ai_use_policy: SourcedValue[str] | None = None

    def verify(self, snapshot: SourceSnapshot) -> bool:
        claims = [self.provider.provenance, self.title.provenance]
        claims.extend(rule.expected.provenance for rule in self.requirements)
        if self.deadline is not None:
            claims.append(self.deadline.provenance)
        if self.award_usd is not None:
            claims.append(self.award_usd.provenance)
        if self.ai_use_policy is not None:
            claims.append(self.ai_use_policy.provenance)
        return all(claim.verifies(snapshot) for claim in claims)


class StudentProfile(StrictRecord):
    student_id: str
    academic_level: str | None = None
    visa_status: str | None = None
    school: str | None = None
    majors: tuple[str, ...] = ()
    gpa: float | None = Field(default=None, ge=0.0, le=4.0)
    consent_to_store: bool = False


class EvidenceItem(StrictRecord):
    id: str
    student_id: str
    statement: str
    confirmed_by_student: bool
    reference: str | None = None


class Application(StrictRecord):
    id: str
    student_id: str
    opportunity_id: str
    status: str = "preparing"
    student_approved: bool = False
    packet_ids: tuple[str, ...] = ()


def all_json_schemas() -> dict[str, dict[str, Any]]:
    models: list[type[BaseModel]] = [SourceSnapshot, ClaimRecord, Requirement, Opportunity,
              StudentProfile, EvidenceItem, Application]
    return {model.__name__: model.model_json_schema() for model in models}
