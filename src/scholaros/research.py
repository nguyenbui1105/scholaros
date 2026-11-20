"""Read-only official-program research: sourced candidates, never automatic eligibility.

A source program landing page is NOT a verified individual scholarship rule.
This module never promotes unreviewed extracted text to ELIGIBLE.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .eligibility import _has_negation, _quote_context, authority_check
from .ingestion import (
    OregonStudentAidConnector,
    PCCFoundationConnector,
    SourceConnector,
    extract_candidates,
    fetch_official,
    source_is_fresh,
)
from .models import Decision
from .records import SourceSnapshot
from .storage import connect

_MANUAL_REVIEWS = (
    "Individual scholarship and award-cycle requirements are unverified",
    "International/F-1 eligibility must be confirmed per individual award",
    "Citizenship and residency restrictions require authoritative review",
    "AI writing and application automation policies are unknown",
    "Program-level dates do not establish individual award cutoffs or timezone",
)


@dataclass(frozen=True)
class ResearchReport:
    provider: str
    source_url: str
    content_hash: str
    retrieved_at: str
    decision: Decision
    verified_awards: int
    ranked: tuple[str, ...]
    candidates: tuple[dict[str, str], ...]
    review_reasons: tuple[str, ...]

    def as_dict(self, *, source_origin: str) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "source_url": self.source_url,
            "content_hash": self.content_hash,
            "retrieved_at": self.retrieved_at,
            "decision": self.decision.value,
            "source_origin": source_origin,
            "verified_awards": self.verified_awards,
            "ranked": list(self.ranked),
            "candidates": list(self.candidates),
            "review_reasons": list(self.review_reasons),
            "submission_status": "NOT_SUBMITTED",
        }


def provider_connector(provider: str) -> SourceConnector:
    if provider == "pcc":
        return PCCFoundationConnector()
    if provider == "osac":
        return OregonStudentAidConnector()
    raise ValueError(f"Unknown provider {provider!r}; select pcc or osac")


def analyze_snapshot(
    provider: str,
    snapshot: SourceSnapshot,
    *,
    now: datetime,
    freshness_days: int = 90,
) -> ResearchReport:
    """Validate immutable snapshot integrity; return quote-backed proposals only.

    Even clean, fresh and positively phrased candidate text cannot by itself
    establish eligibility. An individual program/award and its requirements
    must be manually verified by a competent reviewer.
    """
    connector = provider_connector(provider)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware UTC")
    if snapshot.source_url != connector.url:
        raise ValueError("Source URL does not match the built-in provider registry")
    if not authority_check(snapshot.source_url):
        raise ValueError("Provider source domain failed allowlist screen")
    if sha256(snapshot.text.encode("utf-8")).hexdigest() != snapshot.content_hash:
        raise ValueError("Source snapshot digest mismatch")
    issues = list(_MANUAL_REVIEWS)
    output: list[dict[str, str]] = []
    if not source_is_fresh(snapshot, now, freshness_days):
        issues.append("source_stale")
    else:
        for candidate in extract_candidates(snapshot):
            context = _quote_context(snapshot.text, candidate.quote)
            if context is None or _has_negation(context):
                issues.append(f"negated_or_ambiguous_quote:{candidate.field}")
                continue
            if candidate.quote not in snapshot.text:
                issues.append(f"quote_missing:{candidate.field}")
                continue
            output.append(
                {
                    "field": candidate.field,
                    "value": candidate.value,
                    "quote": candidate.quote,
                    "source_url": candidate.source_url,
                    "content_hash": candidate.content_hash,
                    "retrieved_at": candidate.retrieved_at.isoformat(),
                    "status": "unverified",
                }
            )
    return ResearchReport(
        provider=connector.provider,
        source_url=snapshot.source_url,
        content_hash=snapshot.content_hash,
        retrieved_at=snapshot.retrieved_at.isoformat(),
        decision=Decision.NEEDS_VERIFICATION,
        verified_awards=0,
        ranked=(),
        candidates=tuple(output),
        review_reasons=tuple(dict.fromkeys(issues)),
    )


def persist_public_snapshot(db: sqlite3.Connection, snapshot: SourceSnapshot) -> None:
    """Store immutable public source text only, no student data or credentials."""
    if sha256(snapshot.text.encode("utf-8")).hexdigest() != snapshot.content_hash:
        raise ValueError("Cannot persist a source with an invalid digest")
    with db:
        db.execute(
            """INSERT OR IGNORE INTO public_snapshots
            (content_hash, source_url, retrieved_at, content_text)
            VALUES (?, ?, ?, ?)""",
            (
                snapshot.content_hash,
                snapshot.source_url,
                snapshot.retrieved_at.isoformat(),
                snapshot.text,
            ),
        )


def research_provider(
    provider: str,
    *,
    cache_dir: Path,
    live: bool = False,
    now: datetime | None = None,
    database: Path | None = None,
) -> dict[str, Any]:
    """Offline by default. Live use explicitly opts into provider robots check."""
    connector = provider_connector(provider)
    snapshot = fetch_official(connector, cache_dir=cache_dir, live=live)
    result = analyze_snapshot(provider, snapshot, now=now or datetime.now(UTC))
    if database is not None:
        with connect(database) as db:
            persist_public_snapshot(db, snapshot)
    return result.as_dict(
        source_origin="live_network_unverified" if live else "offline_cache_untrusted"
    )
