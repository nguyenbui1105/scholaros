"""Offline discovery and collection gating, never live network in CI."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from scholaros.collection import (
    CandidateURL,
    CollectionManifest,
    canonical_url,
    collect_offline,
    discover_links,
    validate_manifest,
)
from scholaros.records import SourceSnapshot


def test_canonicalization_and_host_restrictions() -> None:
    assert canonical_url("https://example.edu/scholarship/#overview") == (
        "https://example.edu/scholarship/"
    )
    with pytest.raises(ValueError):
        canonical_url("https://example.edu:8443/scholarship")
    with pytest.raises(ValueError):
        canonical_url("http://example.edu/scholarship")
    with pytest.raises(ValueError):
        canonical_url("https://example.edu@evil.com/scholarship")


def test_discovery_avoids_offsite_login_and_duplicates() -> None:
    html = (
        '<a href="/scholarships/stem">STEM</a>'
        '<a href="https://example.edu/scholarships/stem#details">again</a>'
        '<a href="/login">login</a>'
        '<a href="https://evil.com/scholarships/x">offsite</a>'
    )
    links = discover_links("https://example.edu/scholarships/", html)
    assert links == ["https://example.edu/scholarships/stem"]


def test_missing_permission_prevents_collection() -> None:
    with pytest.raises(PermissionError):
        validate_manifest(
            CollectionManifest(
                approved_by_operator=False,
                terms_checked=False,
                candidates=[CandidateURL(url="https://example.edu/scholarship")],
            )
        )


def test_manifest_is_not_a_verified_collection() -> None:
    manifest = CollectionManifest(
        approved_by_operator=True,
        terms_checked=True,
        candidates=[CandidateURL(url="https://example.edu/scholarship")],
    )
    result = validate_manifest(manifest)
    assert result["candidate_urls"] == 1
    assert result["validated_pages"] == 0


def test_60_offline_snapshots_have_real_hashes_but_no_award_verification(
    tmp_path: Path,
) -> None:
    timestamp = datetime(2026, 11, 19, tzinfo=UTC)
    paths = []
    for i in range(60):
        snap = SourceSnapshot.from_text(
            f"https://example.edu/scholarships/{i:03d}",
            "Fictional scholarship test fixture. No actual awards.",
            timestamp,
        )
        path = tmp_path / f"{i:03d}.json"
        path.write_text(snap.model_dump_json(), encoding="utf-8")
        paths.append(path)
    output = collect_offline(paths, min_pages=50, max_pages=100)
    assert output["snapshots_validated"] == 60
    assert output["official_pages_human_verified"] == 0
    assert output["real_eligibility_labels"] == 0


def test_duplicate_snapshots_not_counted_twice(tmp_path: Path) -> None:
    snap = SourceSnapshot.from_text(
        "https://example.edu/scholarships/a",
        "synthetic",
        datetime(2026, 11, 19, tzinfo=UTC),
    )
    paths = []
    for name in ("a", "b"):
        path = tmp_path / f"{name}.json"
        path.write_text(snap.model_dump_json(), encoding="utf-8")
        paths.append(path)
    with pytest.raises(ValueError, match="minimum"):
        collect_offline(paths, min_pages=2, max_pages=100)


def test_snapshot_hash_tampering_is_blocked(tmp_path: Path) -> None:
    snap = SourceSnapshot.from_text(
        "https://example.edu/scholarships/a",
        "synthetic",
        datetime(2026, 11, 19, tzinfo=UTC),
    ).model_copy(update={"content_hash": "0" * 64})
    path = tmp_path / "fake.json"
    path.write_text(snap.model_dump_json(), encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        collect_offline([path], min_pages=1)
