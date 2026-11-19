"""Permission-aware official-source acquisition with deterministic offline extraction."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from difflib import SequenceMatcher
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from .eligibility import authority_check, normalize
from .records import SourceSnapshot

USER_AGENT = "ScholarOS/0.2 (+https://github.com/nguyenbui1105/scholaros)"
MAX_BYTES = 2_000_000


class SourceConnector(Protocol):
    provider: str
    url: str


@dataclass(frozen=True)
class PCCFoundationConnector:
    provider: str = "Portland Community College Foundation"
    url: str = "https://www.pcc.edu/enroll/paying-for-college/scholarships/apply/"


@dataclass(frozen=True)
class OregonStudentAidConnector:
    provider: str = "Oregon Student Aid (OSAC)"
    url: str = "https://www.oregonstudentaid.gov/scholarships/osac-scholarship-application/"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Request, fp: object, code: int, msg: str, headers: object, newurl: str
    ) -> None:
        raise PermissionError("Cross-site redirects are not followed by ScholarOS")


class _PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _PlainText()
    parser.feed(html)
    return " ".join(" ".join(parser.parts).split())


@dataclass(frozen=True)
class RuleCandidate:
    field: str
    value: str
    quote: str
    source_url: str
    content_hash: str
    retrieved_at: datetime


def _candidate(
    match: re.Match[str], field: str, value: str, snapshot: SourceSnapshot
) -> RuleCandidate | None:
    quote = match.group(0)
    if quote not in snapshot.text:
        return None
    return RuleCandidate(field, value, quote, snapshot.source_url,
                         snapshot.content_hash, snapshot.retrieved_at)


def extract_candidates(snapshot: SourceSnapshot) -> list[RuleCandidate]:
    """Conservative proposals only; these are NOT authoritative eligibility decisions."""
    patterns = (
        ("academic_level", "undergraduate", r"academic level:\s*undergraduate"),
        ("visa_status", "F-1", r"visa:\s*F-1"),
        ("majors", "computer science", r"eligible majors:\s*computer science"),
        ("school", "Demo College", r"eligible schools:\s*Demo College"),
        ("international", "F-1", r"F-1 students (?:may apply|are eligible)"),
        ("international", "international", r"international students (?:may apply|are eligible)"),
        ("min_gpa", "dynamic", r"minimum GPA (?:of |is )?(\d(?:\.\d{1,2})?)"),
        ("deadline", "dynamic", r"deadline:\s*(\d{4}-\d{2}-\d{2})"),
    )
    candidates: list[RuleCandidate] = []
    for field, value, pattern in patterns:
        for match in re.finditer(pattern, snapshot.text, re.IGNORECASE):
            extracted = match.group(1) if value == "dynamic" else value
            item = _candidate(match, field, extracted, snapshot)
            if item:
                candidates.append(item)
    return candidates


def validate_extracted_quote(quote: str, snapshot: SourceSnapshot) -> bool:
    """Reject any LLM-proposed quote not found verbatim in the saved snapshot."""
    return bool(quote.strip()) and quote in snapshot.text


def source_is_fresh(snapshot: SourceSnapshot, now: datetime, days: int = 90) -> bool:
    if days < 0 or now.tzinfo is None:
        raise ValueError("invalid freshness window or naive current time")
    age = (now - snapshot.retrieved_at).total_seconds()
    return 0 <= age <= days * 86400


@dataclass(frozen=True)
class IndexedAward:
    id: str
    provider: str
    title: str
    deadline: date | None


def deduplicate(awards: list[IndexedAward], threshold: float = 0.92) -> list[IndexedAward]:
    """Only merge near-identical titles from one provider in the same cycle."""
    if not 0 < threshold <= 1:
        raise ValueError("threshold must be in (0, 1]")
    unique: list[IndexedAward] = []
    for award in awards:
        if not any(
            normalize(award.provider) == normalize(existing.provider)
            and award.deadline == existing.deadline
            and SequenceMatcher(
                None, normalize(award.title), normalize(existing.title)
            ).ratio() >= threshold
            for existing in unique
        ):
            unique.append(award)
    return unique


def fetch_official(
    connector: SourceConnector, *, cache_dir: Path, live: bool = False,
    min_interval_seconds: float = 2.0,
) -> SourceSnapshot:
    """Network is disabled by default. Fail closed if robots.txt is inaccessible."""
    url = connector.url
    if not authority_check(url) or urlsplit(url).hostname not in {
        "www.pcc.edu", "www.oregonstudentaid.gov"
    }:
        raise PermissionError("Only built-in official connectors may fetch")
    cache_dir.mkdir(parents=True, exist_ok=True)
    name = sha256(url.encode("utf-8")).hexdigest()
    cache_path = cache_dir / f"{name}.json"
    if not live:
        if not cache_path.is_file():
            raise RuntimeError("Offline cache miss: live fetching requires --allow-network")
        stored = json.loads(cache_path.read_text(encoding="utf-8"))
        return SourceSnapshot.model_validate(stored)
    host = urlsplit(url).netloc
    opener = build_opener(_NoRedirect)
    robots_url = f"https://{host}/robots.txt"
    try:
        response = opener.open(Request(robots_url, headers={"User-Agent": USER_AGENT}), timeout=10)
        with response:
            robots = response.read(MAX_BYTES).decode("utf-8", errors="replace")
        parser = RobotFileParser()
        parser.parse(robots.splitlines())
        if not parser.can_fetch(USER_AGENT, url):
            raise PermissionError("robots.txt disallows fetching this source")
        time.sleep(max(0.0, min_interval_seconds))
        with opener.open(Request(url, headers={"User-Agent": USER_AGENT}), timeout=15) as page:
            payload = page.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise ValueError("Remote source exceeds size limit")
    except (OSError, ValueError) as exc:
        raise RuntimeError("Source permission/retrieval not verified; fetch aborted") from exc
    text = html_to_text(payload.decode("utf-8", errors="replace"))
    snapshot = SourceSnapshot.from_text(url, text, datetime.now(UTC))
    cache_path.write_text(snapshot.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return snapshot
