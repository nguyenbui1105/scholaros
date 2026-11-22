"""User-facing local app security and end-to-end tests (red before implementation)."""

from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from scholaros.webui import create_app


@pytest.fixture
def session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, str, Path]:
    monkeypatch.setenv("SCHOLAROS_FERNET_KEY", Fernet.generate_key().decode("ascii"))
    secret = "test-local-access-code"
    packets = tmp_path / "applications.enc"
    app = create_app(
        access_code=secret,
        profile_path=tmp_path / "profile.enc",
        packets_path=packets,
        catalog_path=Path("examples/agent_demo_catalog.json"),
        sources_path=Path("examples/source_discovery_seeds.json"),
    )
    return TestClient(app, base_url="http://localhost"), secret, packets


def unlock(client: TestClient, secret: str) -> None:
    response = client.post("/unlock", data={"access_code": secret}, follow_redirects=False)
    assert response.status_code == 303
    assert "httponly" in response.headers.get("set-cookie", "").lower()
    assert "samesite=strict" in response.headers.get("set-cookie", "").lower()


def csrf(client: TestClient) -> str:
    import re

    html = client.get("/").text
    found = re.search(r'name="csrf" value="([^"]+)"', html)
    assert found is not None
    return found.group(1)


def test_anonymous_and_wrong_code_never_reveal_profile(
    session: tuple[TestClient, str, Path],
) -> None:
    client, secret, _ = session
    assert client.get("/", follow_redirects=False).status_code == 303
    assert "Access code" in client.get("/unlock").text
    assert client.post("/unlock", data={"access_code": "wrong"}).status_code == 403
    assert (
        "scholarship" not in client.get("/unlock").text.lower()
        or secret not in client.get("/unlock").text
    )


def test_requires_csrf_and_rejects_cross_site_origin(session: tuple[TestClient, str, Path]) -> None:
    client, secret, _ = session
    unlock(client, secret)
    assert client.post("/run").status_code == 403
    token = csrf(client)
    assert (
        client.post(
            "/run", data={"csrf": token}, headers={"Origin": "https://attacker.example"}
        ).status_code
        == 403
    )


def test_profile_run_review_and_exact_approval_offline(
    session: tuple[TestClient, str, Path],
) -> None:
    client, secret, packets_path = session
    unlock(client, secret)
    token = csrf(client)
    profile = {
        "csrf": token,
        "student_id": "local-fictitious-student",
        "school": "Demo College",
        "academic_level": "undergraduate",
        "visa_status": "F-1",
        "majors": "computer science",
        "gpa": "3.8",
        "confirmed_story": "I learned programming through personal practice.",
        "consent": "yes",
    }
    saved = client.post("/profile", data=profile, follow_redirects=False)
    assert saved.status_code == 303
    assert client.get("/").status_code == 200
    started = client.post("/run", data={"csrf": token}, follow_redirects=False)
    assert started.status_code == 303
    assert packets_path.exists()
    results = client.get("/applications")
    assert results.status_code == 200
    assert "NOT_SUBMITTED" in results.text
    assert "fictional" in results.text.lower()
    from scholaros.workspace import load_private

    saved_workflow = load_private(packets_path)
    packet = saved_workflow["applications"][0]
    assert packet["submission_status"] == "NOT_SUBMITTED"
    # Not a provider-side action: this only approves the packet for manual use.
    approved = client.post(
        "/approve",
        data={
            "csrf": token,
            "packet_id": packet["id"],
            "packet_hash": packet["packet_hash"],
            "student_confirmed": "yes",
        },
        follow_redirects=False,
    )
    assert approved.status_code == 303
    assert load_private(packets_path)["applications"][0]["approved"] is True
    assert load_private(packets_path)["applications"][0]["submission_status"] == "NOT_SUBMITTED"


def test_no_consent_no_encrypted_profile(session: tuple[TestClient, str, Path]) -> None:
    client, secret, packets_path = session
    unlock(client, secret)
    token = csrf(client)
    response = client.post(
        "/profile",
        data={
            "csrf": token,
            "student_id": "case",
            "gpa": "3.5",
        },
    )
    assert response.status_code == 400
    assert not (packets_path.parent / "profile.enc").exists()


def test_escaped_markup_and_unverified_source_labels(session: tuple[TestClient, str, Path]) -> None:
    client, secret, _ = session
    unlock(client, secret)
    token = csrf(client)
    malicious = '<script>alert("XSS")</script>'
    response = client.post(
        "/profile",
        data={
            "csrf": token,
            "student_id": "student-01",
            "school": malicious,
            "consent": "yes",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    profile_page = client.get("/profile")
    assert malicious not in profile_page.text
    assert "&lt;script&gt;" in profile_page.text
    assert "<script>alert" not in profile_page.text
    assert 'step="any"' in profile_page.text
    sources = client.get("/sources?q=pcc")
    assert sources.status_code == 200
    assert "candidate_unreviewed_terms" in sources.text
    assert "PCC" in sources.text or "pcc.edu" in sources.text
    assert "11 eligible" not in sources.text


def test_host_spoofing_is_rejected(session: tuple[TestClient, str, Path]) -> None:
    client, _, _ = session
    response = client.get("/", headers={"Host": "attacker.example"})
    assert response.status_code == 400


def test_web_requires_encryption_key_before_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SCHOLAROS_FERNET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SCHOLAROS_FERNET_KEY"):
        create_app(
            access_code="secret",
            profile_path=tmp_path / "profile.enc",
            packets_path=tmp_path / "packets.enc",
            catalog_path=Path("examples/agent_demo_catalog.json"),
            sources_path=Path("examples/source_discovery_seeds.json"),
        )


def test_no_remote_network_calls_in_ui(session: tuple[TestClient, str, Path]) -> None:
    client, secret, _ = session
    unlock(client, secret)
    sources = client.get("/sources")
    assert "candidate_unreviewed_terms" in sources.text
    assert 'src="https://' not in sources.text
    assert 'href="https://' in sources.text  # External source links are navigation only.
