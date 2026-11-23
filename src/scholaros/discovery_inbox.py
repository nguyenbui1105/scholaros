"""Opt-in local scholarship discovery inbox; never scrape or certify remote pages.

The operator pastes public index HTML already lawfully obtained. Candidate
URLs are extracted using the existing same-origin HTTPS/link filter and stored
encrypted. They are leads, NOT verified individual awards or eligible matches.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .collection import canonical_url, discover_links
from .source_intake import import_award
from .workspace import load_private, save_private

MAX_INDEX_BYTES = 250_000
MAX_LEADS = 250


class DiscoveryLead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(min_length=16, max_length=16)
    url: str
    index_url: str
    index_hash: str = Field(min_length=64, max_length=64)
    discovered_at: datetime
    status: str = "UNREVIEWED_CANDIDATE"
    eligibility: str = "needs_verification"
    submission_status: str = "NOT_SUBMITTED"


def load_leads(path: Path) -> list[DiscoveryLead]:
    if not path.exists():
        return []
    stored = load_private(path)
    rows = stored.get("leads", [])
    if not isinstance(rows, list):
        raise ValueError("Corrupt discovery inbox")
    return [DiscoveryLead.model_validate(row) for row in rows]


def discover_index(
    path: Path,
    *,
    index_url: str,
    index_html: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Extract same-origin leads from manually supplied HTML; zero HTTP calls."""
    base = canonical_url(index_url.strip())
    if not 20 <= len(index_html) <= MAX_INDEX_BYTES:
        raise ValueError("Index HTML must be 20–250000 characters")
    urls = discover_links(base, index_html)
    current = load_leads(path)
    known = {lead.url for lead in current}
    if len(current) + sum(url not in known for url in urls) > MAX_LEADS:
        raise ValueError("Discovery inbox capacity is 250 unique URLs")
    stamp = now or datetime.now(UTC)
    digest = sha256(index_html.encode("utf-8")).hexdigest()
    added = 0
    for url in urls:
        if url in known:
            continue
        current.append(
            DiscoveryLead(
                id=sha256(url.encode("utf-8")).hexdigest()[:16],
                url=url,
                index_url=base,
                index_hash=digest,
                discovered_at=stamp,
            )
        )
        known.add(url)
        added += 1
    # Even a zero-result import does not create a plaintext index file.
    save_private(path, {"leads": [lead.model_dump(mode="json") for lead in current]})
    return {
        "index_url": base,
        "index_hash": digest,
        "candidate_links_found": len(urls),
        "new_leads": added,
        "total_leads": len(current),
        "verified_awards": 0,
        "submitted_applications": 0,
        "network_requests": 0,
        "status": "UNREVIEWED_CANDIDATES",
    }


def summarize_leads(path: Path, *, search: str = "") -> list[dict[str, Any]]:
    needle = search.strip().casefold()[:80]
    return [
        {
            "id": item.id,
            "url": item.url,
            "index_url": item.index_url,
            "status": item.status,
            "eligibility": item.eligibility,
            "submission_status": item.submission_status,
        }
        for item in load_leads(path)
        if needle in item.url.casefold()
    ]


def promote_with_pasted_text(
    inbox_path: Path,
    awards_path: Path,
    *,
    lead_id: str,
    title: str,
    source_text: str,
) -> dict[str, str]:
    """Explicit user-confirmed page text; keep original lead, no HTTP or approval."""
    lead = next((item for item in load_leads(inbox_path) if item.id == lead_id), None)
    if lead is None:
        raise ValueError("Unknown discovery lead")
    award = import_award(
        awards_path, title=title, source_url=lead.url, source_text=source_text
    )
    return {
        "lead_id": lead.id,
        "award_id": award.id,
        "eligibility": "needs_verification",
        "submission_status": "NOT_SUBMITTED",
        "source_origin": "applicant_pasted_unverified",
    }
