"""Local browser acceptance tests for source-bound provisional profile matching."""

import re
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from scholaros.profile_triage import load_reviews
from scholaros.webui import create_app
from scholaros.workspace_cli import enroll

SOURCE = (
    "The award is open to F-1 international students. Minimum GPA 3.5 is required. "
    "Deadline: 2027-05-01. Applicants must meet additional citizenship and residency rules."
)
URL = "https://scholarships.example.edu/award"


@pytest.fixture
def setup_ui(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, Path]:
    monkeypatch.setenv("SCHOLAROS_FERNET_KEY", Fernet.generate_key().decode())
    profile_path = tmp_path / "profile.enc"
    enroll(profile_path, profile_json=Path("examples/agent_demo_profile.json"))
    reviews_path = tmp_path / "reviews.enc"
    app = create_app(
        access_code="test-matching-access",
        profile_path=profile_path,
        packets_path=tmp_path / "packets.enc",
        imported_sources_path=tmp_path / "sources.enc",
        reviews_path=reviews_path,
        catalog_path=Path("examples/agent_demo_catalog.json"),
        sources_path=Path("examples/source_discovery_seeds.json"),
    )
    client = TestClient(app, base_url="http://localhost")
    client.post("/unlock", data={"access_code": "test-matching-access"})
    return client, reviews_path


def csrf(client: TestClient) -> str:
    match = re.search(r'name="csrf" value="([^"]+)"', client.get("/").text)
    assert match
    return match.group(1)


def insert_source(client: TestClient) -> None:
    assert client.post(
        "/my-sources", follow_redirects=False,
        data={
            "csrf": csrf(client), "title": "2027 Demo Award",
            "source_url": URL, "source_text": SOURCE,
        },
    ).status_code == 303


def test_review_and_preliminary_match_never_claim_eligible(
    setup_ui: tuple[TestClient, Path],
) -> None:
    client, path = setup_ui
    insert_source(client)
    assert "needs_verification" in client.get("/triage").text.lower()
    from scholaros.source_intake import load_awards

    award = load_awards(path.parent / "sources.enc")[0]
    action = client.post(
        "/triage/review",
        follow_redirects=False,
        data={
            "csrf": csrf(client), "award_id": award.id,
            "reviewer_id": "applicant-local", "acknowledged": "yes",
            "min_gpa": "3.5", "gpa_quote": "Minimum GPA 3.5",
            "accepted_visa": "F-1", "visa_quote": "F-1 international students",
            "deadline": "2027-05-01", "deadline_quote": "Deadline: 2027-05-01",
        },
    )
    assert action.status_code == 303
    assert len(load_reviews(path)) == 1
    page = client.get("/triage").text
    assert "potential_match" in page
    assert "NEEDS_VERIFICATION" in page
    assert "NOT_SUBMITTED" in page
    assert "preliminary_match" in page


def test_missing_quote_and_csrf_do_not_write_review(
    setup_ui: tuple[TestClient, Path],
) -> None:
    client, path = setup_ui
    insert_source(client)
    from scholaros.source_intake import load_awards

    award = load_awards(path.parent / "sources.enc")[0]
    data = {
        "award_id": award.id, "reviewer_id": "local", "acknowledged": "yes",
        "accepted_visa": "F-1", "visa_quote": "Invented quote",
    }
    assert client.post("/triage/review", data=data).status_code == 403
    assert client.post(
        "/triage/review", data={**data, "csrf": csrf(client)}
    ).status_code == 400
    assert client.post(
        "/triage/review", data={**data, "csrf": csrf(client)},
        headers={"Origin": "https://attacker.example"},
    ).status_code == 403
    assert load_reviews(path) == []
