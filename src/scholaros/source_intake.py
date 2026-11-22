"""Local intake for *actual* individual-award page text, without invented verification.

The applicant copies source text from a publicly accessible official page they
are allowed to use. No HTTP requests are made, and a self-supplied URL/quote is
never proof that the provider endorses the award or that F-1 eligibility holds.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

from .eligibility import _has_negation, _quote_context, authority_check
from .ingestion import extract_candidates, html_to_text
from .records import SourceSnapshot
from .workspace import load_private, save_private

MAX_SOURCE_TEXT = 120_000
MAX_AWARDS = 100


class ImportedAward(BaseModel):
    """Unverified applicant-submitted page snapshot (not a vetted scholarship)."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    title: str = Field(min_length=2, max_length=180)
    source_url: str
    source_text: str = Field(min_length=40, max_length=MAX_SOURCE_TEXT)
    content_hash: str
    imported_at: datetime
    origin: str = "applicant_pasted_unverified"
    decision: str = "needs_verification"
    submission_status: str = "NOT_SUBMITTED"
    candidates: list[dict[str, str]]
    review_queue: list[str]


def _check_url(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.port not in (None, 443)
        or not authority_check(url)
    ):
        raise ValueError("Only plausible HTTPS institutional source URLs are accepted")
    return url


def parse_award(
    *,
    title: str,
    source_url: str,
    source_text: str,
    imported_at: datetime | None = None,
) -> ImportedAward:
    """Extract only literal quote candidates; never promote self-supplied evidence."""
    url = _check_url(source_url.strip())
    if not 2 <= len(title.strip()) <= 180:
        raise ValueError("An individual scholarship title is required")
    if not source_text.strip() or len(source_text) > MAX_SOURCE_TEXT:
        raise ValueError("Scholarship text must be nonempty and within the size limit")
    if "<" in source_text and ">" in source_text:
        source_text = html_to_text(source_text)
    content = " ".join(source_text.split())
    if len(content) < 40 or len(content) > MAX_SOURCE_TEXT:
        raise ValueError("Source text must contain at least 40 visible characters")
    timestamp = imported_at or datetime.now(UTC)
    snapshot = SourceSnapshot.from_text(url, content, timestamp)
    candidates: list[dict[str, str]] = []
    queue: list[str] = []
    for item in extract_candidates(snapshot):
        context = _quote_context(snapshot.text, item.quote)
        if context is None or _has_negation(context):
            queue.append(f"Conflicting or negated rule near {item.field}")
            continue
        candidates.append({
            "field": item.field, "value": item.value, "quote": item.quote,
            "source_url": url, "content_hash": snapshot.content_hash,
            "status": "unverified",
        })
    queue.extend([
        "Confirm that the URL belongs to the actual award provider and this is the current cycle",
        "Verify F-1 / international student eligibility including citizenship and residency",
        "Verify GPA, school, academic level, major, and all additional award conditions",
        "Confirm deadline, timezone, award amount, and required documents",
        "Check provider AI-writing policy and obtain human approval of the final essay",
        "Review the official application portal and submit manually; no submission performed",
    ])
    award_id = sha256((url + "\n" + snapshot.content_hash).encode("utf-8")).hexdigest()[:24]
    return ImportedAward(
        id=award_id,
        title=title.strip(),
        source_url=url,
        source_text=content,
        content_hash=snapshot.content_hash,
        imported_at=timestamp,
        candidates=candidates,
        review_queue=list(dict.fromkeys(queue)),
    )


def load_awards(path: Path) -> list[ImportedAward]:
    if not path.is_file():
        return []
    data = load_private(path)
    records = data.get("awards")
    if not isinstance(records, list):
        raise ValueError("Invalid encrypted award registry")
    return [ImportedAward.model_validate(item) for item in records]


def import_award(
    path: Path, *, title: str, source_url: str, source_text: str
) -> ImportedAward:
    award = parse_award(title=title, source_url=source_url, source_text=source_text)
    records = load_awards(path)
    if any(item.id == award.id for item in records):
        return next(item for item in records if item.id == award.id)
    if len(records) >= MAX_AWARDS:
        raise ValueError("Local source registry reached its safety limit of 100")
    records.append(award)
    save_private(path, {"awards": [item.model_dump(mode="json") for item in records]})
    return award


def summarize_awards(path: Path, *, search: str = "") -> list[dict[str, Any]]:
    term = re.sub(r"\s+", " ", search.strip().casefold())[:80]
    output: list[dict[str, Any]] = []
    for award in load_awards(path):
        if term not in (award.title + " " + award.source_url).casefold():
            continue
        output.append({
            "id": award.id,
            "title": award.title,
            "source_url": award.source_url,
            "content_hash": award.content_hash,
            "origin": award.origin,
            "decision": award.decision,
            "submission_status": award.submission_status,
            "candidates": [dict(item) for item in award.candidates],
            "review_queue": list(award.review_queue),
            "imported_at": award.imported_at.isoformat(),
        })
    return output
