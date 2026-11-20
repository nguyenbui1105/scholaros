"""Permission-gated URL discovery and snapshot validation for research corpora.

Robots permission is necessary but NOT sufficient: operators attest that
provider terms permit the requested access. Network activity is opt-in.
"""

from __future__ import annotations

import re
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from pydantic import BaseModel, ConfigDict, Field

from .eligibility import authority_check
from .records import SourceSnapshot

USER_AGENT = "ScholarOS-Research/0.3.1 (+https://github.com/nguyenbui1105/scholaros)"
MAX_RESPONSE_BYTES = 1_000_000
BLOCKED_PATHS = re.compile(
    r"/(?:login|signin|sign-in|auth|portal|account|apply|checkout|admin)(?:/|$)",
    re.IGNORECASE,
)
SCHOLARSHIP_PATH = re.compile(
    r"(scholarship|fellowship|financial-aid|financialaid|funding|award)",
    re.IGNORECASE,
)


class CandidateURL(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    url: str
    discovered_from: str | None = None
    status: str = "candidate_unverified"


class CollectionManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    approved_by_operator: bool
    terms_checked: bool
    operator_id: str = "local-operator"
    candidates: list[CandidateURL]
    max_pages: int = Field(default=100, ge=1, le=100)
    min_interval_seconds: float = Field(default=2.0, ge=1.0)


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            for key, value in attrs:
                if key == "href" and value:
                    self.hrefs.append(value)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Request, fp: object, code: int, msg: str, headers: object, newurl: str
    ) -> None:
        raise PermissionError("ScholarOS does not follow remote redirects")


def canonical_url(url: str) -> str:
    """Normalize HTTPS hostname/path and strip fragment; reject credentials and odd ports."""
    parts = urlsplit(url)
    if (
        parts.scheme.lower() != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.port not in (None, 443)
    ):
        raise ValueError("Unsafe or non-HTTPS candidate URL")
    host = parts.hostname.encode("idna").decode("ascii").lower()
    if not authority_check("https://" + host + "/"):
        raise ValueError("Candidate host is not a recognized official-domain class")
    if BLOCKED_PATHS.search(parts.path):
        raise ValueError("Login, account and application flows are out of scope")
    if parts.query and any(key in parts.query.lower() for key in ("token=", "session=", "key=")):
        raise ValueError("Candidate contains potentially sensitive URL parameters")
    path = parts.path or "/"
    return urlunsplit(("https", host, path, parts.query, ""))


def discover_links(base_url: str, html: str) -> list[str]:
    """Same-origin links with scholarship-like paths, never off-site auto-crawling."""
    base = canonical_url(base_url)
    host = urlsplit(base).hostname
    parser = _LinkParser()
    parser.feed(html)
    found: set[str] = set()
    for href in parser.hrefs:
        try:
            candidate = canonical_url(urljoin(base, href))
            parsed = urlsplit(candidate)
            if (
                parsed.hostname == host
                and SCHOLARSHIP_PATH.search(parsed.path)
                and not parsed.path.lower().endswith((".pdf", ".doc", ".docx", ".zip"))
            ):
                found.add(candidate)
        except (ValueError, UnicodeError):
            continue
    return sorted(found)


def validate_manifest(manifest: CollectionManifest) -> dict[str, int]:
    if not manifest.approved_by_operator or not manifest.terms_checked:
        raise PermissionError("Explicit operator approval AND provider terms review required")
    urls = [canonical_url(item.url) for item in manifest.candidates]
    if len(set(urls)) != len(urls):
        raise ValueError("Manifest contains duplicate URLs")
    if len(urls) > manifest.max_pages:
        raise ValueError("Manifest exceeds max_pages")
    return {"candidate_urls": len(urls), "validated_pages": 0}


def collect_offline(
    paths: Iterable[Path], *, min_pages: int = 50, max_pages: int = 100
) -> dict[str, int]:
    """Audit local snapshots, never claim they are human-verified official sources."""
    if min_pages < 1 or max_pages > 100 or min_pages > max_pages:
        raise ValueError("Invalid 50-100 page collection range")
    seen_urls: set[str] = set()
    seen_hashes: set[str] = set()
    for path in paths:
        snapshot = SourceSnapshot.model_validate_json(path.read_text(encoding="utf-8"))
        url = canonical_url(snapshot.source_url)
        digest = sha256(snapshot.text.encode("utf-8")).hexdigest()
        if snapshot.content_hash != digest:
            raise ValueError("Snapshot hash does not match its text")
        if url in seen_urls:
            continue
        seen_urls.add(url)
        seen_hashes.add(digest)
        if len(seen_urls) > max_pages:
            raise ValueError("Collection exceeded maximum")
    if len(seen_urls) < min_pages:
        raise ValueError(f"Collection below minimum of {min_pages} distinct pages")
    return {
        "snapshots_validated": len(seen_urls),
        "distinct_content_hashes": len(seen_hashes),
        "official_pages_human_verified": 0,
        "real_eligibility_labels": 0,
    }


def collect_authorized(
    manifest: CollectionManifest, *,
    cache_dir: Path,
    allow_network: bool = False,
    min_pages: int = 50,
) -> dict[str, int]:
    """Operator-authorized bounded retrieval; fail closed on robots/terms uncertainty.

    This function is never used in CI. Reject redirects and non-HTML responses;
    operate only on the exact allowlisted hosts in the approved manifest.
    """
    validate_manifest(manifest)
    if not allow_network:
        raise PermissionError("Live collection requires explicit allow_network=True")
    if not 50 <= min_pages <= 100:
        raise ValueError("Live collection target must be 50 to 100 pages")
    if len(manifest.candidates) < min_pages:
        raise ValueError("Not enough individually approved candidate URLs")

    cache_dir.mkdir(parents=True, exist_ok=True)
    opener = build_opener(_NoRedirect)
    robots_by_host: dict[str, RobotFileParser] = {}
    paths: list[Path] = []
    last_request: dict[str, float] = {}

    for candidate in manifest.candidates:
        url = canonical_url(candidate.url)
        host = urlsplit(url).netloc
        if host not in robots_by_host:
            robots_url = f"https://{host}/robots.txt"
            with opener.open(
                Request(robots_url, headers={"User-Agent": USER_AGENT}), timeout=10
            ) as robots_page:
                if robots_page.status != 200:
                    raise PermissionError(f"Robots unavailable for {host}")
                robots_text = robots_page.read(MAX_RESPONSE_BYTES).decode(
                    "utf-8", errors="replace"
                )
            parser = RobotFileParser()
            parser.parse(robots_text.splitlines())
            robots_by_host[host] = parser
        if not robots_by_host[host].can_fetch(USER_AGENT, url):
            raise PermissionError(f"robots.txt disallows {url}")

        elapsed = time.monotonic() - last_request.get(host, 0.0)
        if elapsed < manifest.min_interval_seconds:
            time.sleep(manifest.min_interval_seconds - elapsed)
        last_request[host] = time.monotonic()

        with opener.open(Request(url, headers={"User-Agent": USER_AGENT}), timeout=15) as page:
            if page.status != 200 or "text/html" not in page.headers.get("Content-Type", ""):
                raise ValueError("Only successful HTML content may be collected")
            raw = page.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Page exceeds response size limit")
        from .ingestion import html_to_text

        snapshot = SourceSnapshot.from_text(
            url, html_to_text(raw.decode("utf-8", errors="replace")), datetime.now(UTC)
        )
        path = cache_dir / (sha256(url.encode("utf-8")).hexdigest() + ".json")
        path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
        paths.append(path)

    return collect_offline(paths, min_pages=min_pages, max_pages=manifest.max_pages)


def save_candidates(path: Path, urls: list[str], *, discovered_from: str) -> None:
    """Write unreviewed candidates as JSON, never imply permission or eligibility."""
    manifest = CollectionManifest(
        approved_by_operator=False, terms_checked=False,
        candidates=[CandidateURL(url=url, discovered_from=discovered_from) for url in urls],
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")


def load_manifest(path: Path) -> CollectionManifest:
    return CollectionManifest.model_validate_json(path.read_text(encoding="utf-8"))
