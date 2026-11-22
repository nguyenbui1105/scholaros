"""Evidence-first source import: real page text never becomes automatic eligibility."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from scholaros.source_intake import (
    ImportedAward,
    import_award,
    load_awards,
    parse_award,
    summarize_awards,
)
from scholaros.webui import create_app

URL = "https://scholarships.example.edu/individual-award"
TEXT = (
    "International students may apply. F-1 students may apply. "
    "Minimum GPA 3.0. Deadline: 2027-04-01. "
    "Check other requirements, including residency and citizenship restrictions."
)


def test_real_source_input_stays_unverified() -> None:
    award = parse_award(
        title="Individual STEM Scholarship", source_url=URL, source_text=TEXT,
        imported_at=datetime(2026, 11, 22, tzinfo=UTC),
    )
    assert isinstance(award, ImportedAward)
    assert award.decision == "needs_verification"
    assert award.submission_status == "NOT_SUBMITTED"
    assert award.origin == "applicant_pasted_unverified"
    assert award.content_hash == sha256(award.source_text.encode()).hexdigest()
    assert award.review_queue
    assert all(c["status"] == "unverified" for c in award.candidates)
    assert all(c["quote"] in award.source_text for c in award.candidates)
    assert any("F-1" in c["quote"] for c in award.candidates)


@pytest.mark.parametrize(
    "invalid_url",
    [
        "http://scholarships.example.edu/award",
        "https://example.com/award",
        "https://student:password@example.edu/award",
        "https://example.edu:8080/award",
        "https://example.edu/award#fragment",
        "https://example.edu@evil.example/award",
    ],
)
def test_reject_untrusted_url(invalid_url: str) -> None:
    with pytest.raises(ValueError):
        parse_award(title="Award", source_url=invalid_url, source_text=TEXT)


def test_short_text_and_missing_title_fail() -> None:
    with pytest.raises(ValueError, match="title"):
        parse_award(title=" ", source_url=URL, source_text=TEXT)
    with pytest.raises(ValueError, match="text"):
        parse_award(title="Award", source_url=URL, source_text="Too short")
    with pytest.raises(ValueError, match="limit"):
        parse_award(title="Award", source_url=URL, source_text="A" * 120_001)


def test_negation_suppresses_positive_candidate() -> None:
    award = parse_award(
        title="Exclusive Award", source_url=URL,
        source_text=(
            "F-1 students may apply except those holding F-1 visas. "
            "Other criteria include local residency and citizenship requirements."
        ),
    )
    assert not any(item["field"] == "international" for item in award.candidates)
    assert any("negated" in item.lower() for item in award.review_queue)


def test_pasted_html_is_plain_text_and_never_rendered_as_script() -> None:
    raw = "<script>window.location='https://bad.example/'</script><p>" + TEXT + "</p>"
    award = parse_award(title="<script>alert(1)</script>", source_url=URL, source_text=raw)
    assert "<script>" not in award.source_text
    assert "window.location" not in award.source_text
    assert award.decision == "needs_verification"


def test_encrypted_registry_duplicate_and_versioning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SCHOLAROS_FERNET_KEY", Fernet.generate_key().decode())
    path = tmp_path / "source_awards.enc"
    one = import_award(path, title="Individual award", source_url=URL, source_text=TEXT)
    again = import_award(path, title="Individual award", source_url=URL, source_text=TEXT)
    assert one.id == again.id
    newer = import_award(
        path, title="Individual award", source_url=URL,
        source_text=TEXT + " Newly updated application instructions this cycle.",
    )
    assert one.id != newer.id
    assert len(load_awards(path)) == 2
    assert b"F-1 students may apply" not in path.read_bytes()
    results = summarize_awards(path, search="Individual")
    assert len(results) == 2
    assert all("source_text" not in row for row in results)
    assert summarize_awards(path, search="nonexistent") == []


def test_missing_or_wrong_encryption_key_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "registry.enc"
    monkeypatch.delenv("SCHOLAROS_FERNET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        import_award(path, title="Award", source_url=URL, source_text=TEXT)
    monkeypatch.setenv("SCHOLAROS_FERNET_KEY", Fernet.generate_key().decode())
    import_award(path, title="Award", source_url=URL, source_text=TEXT)
    monkeypatch.setenv("SCHOLAROS_FERNET_KEY", Fernet.generate_key().decode())
    with pytest.raises(Exception):
        load_awards(path)


def test_source_import_ui_requires_auth_csrf_and_escapes_html(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SCHOLAROS_FERNET_KEY", Fernet.generate_key().decode())
    app = create_app(
        access_code="a-long-secret-code",
        profile_path=tmp_path / "student.enc",
        packets_path=tmp_path / "packets.enc",
        imported_sources_path=tmp_path / "source_awards.enc",
        catalog_path=Path("examples/agent_demo_catalog.json"),
        sources_path=Path("examples/source_discovery_seeds.json"),
    )
    client = TestClient(app, base_url="http://localhost")
    assert client.get("/my-sources", follow_redirects=False).status_code == 303
    assert client.post("/my-sources", data={
        "title": "Award", "source_url": URL, "source_text": TEXT
    }).status_code == 403
    assert client.post("/unlock", data={"access_code": "a-long-secret-code"}).status_code == 200
    assert client.post("/my-sources", data={
        "title": "Award", "source_url": URL, "source_text": TEXT
    }).status_code == 403
    import re

    home = client.get("/").text
    match = re.search(r'name="csrf" value="([^"]+)"', home)
    assert match
    token = match.group(1)
    assert client.post("/my-sources", data={
        "csrf": token, "title": "Award", "source_url": URL, "source_text": TEXT,
    }, headers={"Origin": "https://evil.example"}).status_code == 403
    response = client.post("/my-sources", data={
        "csrf": token, "title": "<script>alert(1)</script>",
        "source_url": URL, "source_text": TEXT,
    }, follow_redirects=False)
    assert response.status_code == 303
    output = client.get("/my-sources")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in output.text
    assert "<script>alert(1)</script>" not in output.text
    assert "NEEDS_VERIFICATION" in output.text
    assert "NOT_SUBMITTED" in output.text
    assert "F-1 students may apply" in output.text
    assert len(load_awards(tmp_path / "source_awards.enc")) == 1
