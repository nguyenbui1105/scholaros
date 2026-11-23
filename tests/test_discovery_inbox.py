"""All discovery steps are local, source-safe, encrypted, and opt-in."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from scholaros.discovery_inbox import (
    discover_index,
    load_leads,
    promote_with_pasted_text,
    summarize_leads,
)
from scholaros.source_intake import load_awards
from scholaros.webui import create_app

INDEX = "https://scholarships.example.edu/scholarships/"
HTML = (
    '<html><a href="/scholarships/stem-award">STEM</a>'
    '<a href="/scholarships/stem-award">duplicate</a>'
    '<a href="https://evil.example/award">external</a>'
    '<a href="/login">Login</a>'
    '<a href="/scholarships/stem-award.pdf">PDF</a>'
    '<a href="/scholarships/another-award">another</a></html>'
)
AWARD_TEXT = (
    "Individual undergraduate scholarship applications are open. "
    "The F-1 eligibility terms must be independently confirmed. "
    "Deadline: 2027-06-30. Check all other requirements."
)


@pytest.fixture
def key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCHOLAROS_FERNET_KEY", Fernet.generate_key().decode())


def test_discovery_dedup_same_origin_and_no_authority_claim(tmp_path: Path, key: None) -> None:
    inbox = tmp_path / "leads.enc"
    result = discover_index(inbox, index_url=INDEX, index_html=HTML)
    assert result["candidate_links_found"] == 2
    assert result["new_leads"] == 2
    assert result["verified_awards"] == 0
    assert result["network_requests"] == 0
    leads = load_leads(inbox)
    assert len(leads) == 2
    assert all(item.url.startswith("https://scholarships.example.edu/") for item in leads)
    assert all(item.eligibility == "needs_verification" for item in leads)
    assert all(item.submission_status == "NOT_SUBMITTED" for item in leads)
    again = discover_index(inbox, index_url=INDEX, index_html=HTML)
    assert again["new_leads"] == 0
    assert len(load_leads(inbox)) == 2


def test_promote_requires_explicit_text_and_stays_unverified(tmp_path: Path, key: None) -> None:
    inbox, awards = tmp_path / "inbox.enc", tmp_path / "awards.enc"
    discover_index(inbox, index_url=INDEX, index_html=HTML)
    lead = load_leads(inbox)[0]
    with pytest.raises(ValueError, match="Unknown"):
        promote_with_pasted_text(
            inbox,
            awards,
            lead_id="not-in-inbox",
            title="Award",
            source_text=AWARD_TEXT,
        )
    result = promote_with_pasted_text(
        inbox,
        awards,
        lead_id=lead.id,
        title="Example award",
        source_text=AWARD_TEXT,
    )
    assert result["eligibility"] == "needs_verification"
    assert result["submission_status"] == "NOT_SUBMITTED"
    assert len(load_awards(awards)) == 1
    assert load_awards(awards)[0].source_url == lead.url
    assert len(load_leads(inbox)) == 2
    assert b"Individual undergraduate" not in awards.read_bytes()


@pytest.mark.parametrize(
    "base",
    [
        "https://example.com/scholarships",
        "http://scholarships.example.edu/scholarships",
        "https://scholarships.example.edu:444/scholarships",
        "https://scholarships.example.edu@attacker.example/scholarships",
    ],
)
def test_bad_source_rejected(tmp_path: Path, key: None, base: str) -> None:
    with pytest.raises(ValueError):
        discover_index(tmp_path / "leads.enc", index_url=base, index_html=HTML)


def test_no_key_refuses_to_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCHOLAROS_FERNET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        discover_index(tmp_path / "leads.enc", index_url=INDEX, index_html=HTML)


def test_search_and_zero_raw_index_storage(tmp_path: Path, key: None) -> None:
    inbox = tmp_path / "leads.enc"
    discover_index(inbox, index_url=INDEX, index_html=HTML)
    assert len(summarize_leads(inbox, search="stem")) == 1
    assert summarize_leads(inbox, search="none") == []
    assert b"/scholarships/stem-award" not in inbox.read_bytes()


def test_web_auth_csrf_and_import_workflow(tmp_path: Path, key: None) -> None:
    inbox = tmp_path / "leads.enc"
    awards = tmp_path / "awards.enc"
    app = create_app(
        access_code="long-secret-access-code",
        profile_path=tmp_path / "profile.enc",
        packets_path=tmp_path / "packets.enc",
        imported_sources_path=awards,
        discovery_path=inbox,
        catalog_path=Path("examples/agent_demo_catalog.json"),
        sources_path=Path("examples/source_discovery_seeds.json"),
    )
    client = TestClient(app, base_url="http://localhost")
    assert client.get("/discover", follow_redirects=False).status_code == 303
    assert (
        client.post("/discover", data={"index_url": INDEX, "index_html": HTML}).status_code == 403
    )
    client.post("/unlock", data={"access_code": "long-secret-access-code"})
    match = re.search(r'name="csrf" value="([^"]+)"', client.get("/").text)
    assert match
    csrf = match.group(1)
    assert (
        client.post(
            "/discover",
            data={
                "csrf": csrf,
                "index_url": INDEX,
                "index_html": HTML,
            },
            headers={"Origin": "https://attacker.example"},
        ).status_code
        == 403
    )
    saved = client.post(
        "/discover",
        data={
            "csrf": csrf,
            "index_url": INDEX,
            "index_html": HTML,
        },
        follow_redirects=False,
    )
    assert saved.status_code == 303
    assert "UNREVIEWED_CANDIDATE" in client.get("/discover").text
    lead = load_leads(inbox)[0]
    imported = client.post(
        "/discover/import",
        data={
            "csrf": csrf,
            "lead_id": lead.id,
            "title": "Local example",
            "source_text": AWARD_TEXT,
        },
        follow_redirects=False,
    )
    assert imported.status_code == 303
    assert len(load_awards(awards)) == 1
    assert "NEEDS_VERIFICATION" in client.get("/my-sources").text
    assert "NOT_SUBMITTED" in client.get("/applications").text
