"""Local-only student experience with encrypted state and explicit packet approval.

Security boundary: bind only to 127.0.0.1; require an ephemeral login token,
SameSite=Strict HttpOnly cookie, per-session CSRF and trusted hosts. No network
calls, no hosted auth, no provider submission. Never expose raw exception text.
"""

from __future__ import annotations

import hmac
import json
import os
import secrets
from datetime import date
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from starlette.datastructures import FormData
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .records import EvidenceItem, StudentProfile
from .source_intake import import_award, summarize_awards
from .workspace import ApplicantBundle, load_private, save_private
from .workspace_cli import approve, execute

_STYLES = """
:root{color-scheme:light;--ink:#172b36;--muted:#60747c;--line:#dce5e8;--accent:#22756d;--paper:#fff;--bg:#f4f8f7}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);font:15px/1.6 system-ui,-apple-system,Segoe UI,sans-serif;color:var(--ink)}
a{color:#185e59;text-decoration:none}a:hover{text-decoration:underline}
header{background:#123735;color:white;padding:24px 0}
.shell{max-width:1100px;margin:0 auto;padding:0 22px}
.brand{font-weight:800;font-size:22px;letter-spacing:-.5px}header a{color:#e6f7f3}
header nav{display:flex;gap:20px;flex-wrap:wrap;margin-top:10px}
main{padding:32px 22px 80px!important}
h1{font-size:clamp(28px,4vw,45px);line-height:1.2;letter-spacing:-1.2px;margin:0 0 12px}
h2{font-size:21px;margin:0 0 14px}
.lead{font-size:17px;color:var(--muted);max-width:740px}
.panel{background:var(--paper);padding:24px;margin:18px 0;border:1px solid var(--line);border-radius:16px;box-shadow:0 4px 28px #193c3510}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:18px}
.pill{display:inline-block;border-radius:40px;padding:4px 11px;background:#e6f5ee;color:#245d53;font-weight:700;font-size:12px}
.warn{background:#fff8e7;border-left:4px solid #b57b24;padding:13px 16px;border-radius:6px;margin:18px 0}
.note{color:var(--muted);font-size:13px}
label{display:block;font-weight:650;margin:14px 0 5px}
input,textarea,select{width:100%;max-width:700px;font:inherit;border:1px solid #bfcfce;border-radius:9px;padding:11px;color:var(--ink);background:#fff}
input[type=checkbox]{width:auto;margin-right:8px}
button,.button{display:inline-block;padding:11px 18px;border:0;border-radius:10px;background:#176e63;color:white;font-weight:750;cursor:pointer;margin:12px 7px 0 0}
button:hover{background:#10574f}.button.secondary{background:#e8f4f1;color:#165f57}
.card-title{font-weight:750;font-size:17px}
pre{white-space:pre-wrap;overflow-wrap:anywhere}
code{background:#edf3f1;padding:2px 5px;border-radius:4px}
dl{display:grid;grid-template-columns:minmax(120px,1fr) 2fr;gap:9px}
dt{color:var(--muted)}dd{margin:0;overflow-wrap:anywhere}
details{padding:12px 0;border-top:1px solid var(--line)}
summary{cursor:pointer;font-weight:650}
footer{padding:32px;color:var(--muted);text-align:center}
@media(max-width:620px){.panel{padding:18px}dl{grid-template-columns:1fr}main{padding-top:20px!important}}
"""


def _text(value: object) -> str:
    return escape(str(value) if value is not None else "", quote=True)


def _field(form: FormData, name: str) -> str:
    value = form.get(name)
    return value.strip() if isinstance(value, str) else ""


def _html(title: str, contents: str, *, authenticated: bool = True) -> HTMLResponse:
    nav = (
        '<nav><a href="/">Dashboard</a><a href="/profile">My profile</a>'
        '<a href="/sources">Scholarship sources</a>'
        '<a href="/my-sources">My researched awards</a>'
        '<a href="/applications">Applications</a></nav>'
        if authenticated
        else ""
    )
    body = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_text(title)} | ScholarOS</title><style>{_STYLES}</style></head>"
        '<body><header><div class="shell"><span class="brand">✳ ScholarOS</span>'
        f'{nav}</div></header><main class="shell">{contents}</main>'
        "<footer>Local research workspace · No automated submissions · "
        "Not legal or financial-aid advice</footer></body></html>"
    )
    return HTMLResponse(body)


def _input(
    label: str, field: str, value: object = "", *, required: bool = False, kind: str = "text"
) -> str:
    req = " required" if required else ""
    number_opts = ' step="any" min="0" max="4"' if kind == "number" else ""
    return (
        f'<label for="{field}">{_text(label)}</label>'
        f'<input id="{field}" name="{field}" type="{kind}" '
        f'value="{_text(value)}"{req}{number_opts}>'
    )


def create_app(
    *,
    access_code: str,
    profile_path: Path,
    packets_path: Path,
    catalog_path: Path,
    sources_path: Path,
    imported_sources_path: Path | None = None,
) -> FastAPI:
    """Create one local user instance. This is NOT a public multi-user service."""
    if not os.environ.get("SCHOLAROS_FERNET_KEY"):
        raise RuntimeError("SCHOLAROS_FERNET_KEY must be configured before web startup")
    research_store = imported_sources_path or profile_path.parent / "source_awards.enc"
    if len(access_code) < 8:
        raise ValueError("Local access code is too short")
    app = FastAPI(
        title="ScholarOS Local Student Workspace",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "[::1]"],
    )
    session = secrets.token_urlsafe(40)
    csrf_value = secrets.token_urlsafe(40)

    def authorized(request: Request) -> bool:
        cookie = request.cookies.get("scholaros_session", "")
        return hmac.compare_digest(cookie, session)

    def safe_post(request: Request, form: FormData, *, login: bool = False) -> bool:
        origin = request.headers.get("origin")
        if origin:
            try:
                parts = urlsplit(origin)
                if (
                    parts.scheme != "http"
                    or parts.hostname not in {"localhost", "127.0.0.1", "::1"}
                    or parts.port != request.url.port
                ):
                    return False
            except ValueError:
                return False
        if request.headers.get("sec-fetch-site") == "cross-site":
            return False
        return login or (
            authorized(request) and hmac.compare_digest(_field(form, "csrf"), csrf_value)
        )

    def gate(request: Request) -> Response | None:
        if not authorized(request):
            return RedirectResponse("/unlock", status_code=303)
        return None

    def csrf() -> str:
        return f'<input type="hidden" name="csrf" value="{_text(csrf_value)}">'

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; "
            "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/unlock", response_class=HTMLResponse)
    async def unlock_page() -> HTMLResponse:
        return _html(
            "Unlock",
            '<section class="panel"><h1>Unlock your workspace</h1>'
            '<p class="lead">Enter the access code shown in the terminal. '
            "All applicant records are stored locally with encryption.</p>"
            '<form method="post" action="/unlock">'
            '<label for="access_code">Access code</label>'
            '<input id="access_code" type="password" name="access_code" required>'
            '<button type="submit">Unlock</button></form></section>',
            authenticated=False,
        )

    @app.post("/unlock")
    async def unlock(request: Request) -> Response:
        form = await request.form()
        if not safe_post(request, form, login=True) or not hmac.compare_digest(
            _field(form, "access_code"), access_code
        ):
            return HTMLResponse("Access denied", status_code=403)
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            "scholaros_session",
            session,
            httponly=True,
            secure=False,
            samesite="strict",
            path="/",
            max_age=3600,
        )
        return response

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request) -> Response:
        denied = gate(request)
        if denied:
            return denied
        profile_exists = profile_path.is_file()
        packets_exist = packets_path.is_file()
        intro = (
            "<h1>Your scholarship workspace</h1>"
            '<p class="lead">Enter verified facts once, explore official source '
            "candidates, and prepare application packets with a human approval gate.</p>"
            '<div class="warn"><strong>Research alpha:</strong> The built-in award '
            "catalog is fictional. Official source links are unverified candidates; "
            "we do not automatically submit applications.</div>"
        )
        panels = (
            '<div class="grid"><section class="panel"><span class="pill">Step 1</span>'
            "<h2>Student profile</h2>"
            f"<p>{('Encrypted profile saved' if profile_exists else 'Not yet configured')}</p>"
            '<a class="button" href="/profile">Edit profile</a></section>'
            '<section class="panel"><span class="pill">Step 2</span>'
            "<h2>Scholarship sources</h2><p>Explore institutional starting points "
            "with explicit source-verification warnings.</p>"
            '<a class="button secondary" href="/sources">Browse sources</a>'
            '<a class="button secondary" href="/my-sources">Import an award page</a></section>'
            '<section class="panel"><span class="pill">Step 3</span>'
            "<h2>Agent workflow</h2>"
            f"<p>{('Review packets below' if packets_exist else 'Prepare a review packet')}</p>"
            '<form method="post" action="/run">'
            f'{csrf()}<button type="submit">Run agents (demo)</button></form>'
            "</section></div>"
        )
        return _html("Dashboard", intro + panels)

    @app.get("/profile", response_class=HTMLResponse)
    async def profile(request: Request) -> Response:
        denied = gate(request)
        if denied:
            return denied
        existing: dict[str, Any] = {}
        story = ""
        if profile_path.is_file():
            profile_data = ApplicantBundle.model_validate(load_private(profile_path))
            existing = profile_data.student.model_dump()
            story = next(
                (item.statement for item in profile_data.evidence if item.confirmed_by_student), ""
            )
        fields = (
            _input(
                "Local ID (not your full name)",
                "student_id",
                existing.get("student_id"),
                required=True,
            )
            + _input("School", "school", existing.get("school"))
            + _input("Visa category (e.g. F-1)", "visa_status", existing.get("visa_status"))
            + _input("Academic level", "academic_level", existing.get("academic_level"))
            + _input("Majors (comma separated)", "majors", ", ".join(existing.get("majors") or []))
            + _input("GPA (0.0–4.0, blank if unknown)", "gpa", existing.get("gpa"), kind="number")
        )
        content = (
            '<section class="panel"><h1>My profile</h1>'
            '<p class="note">Do not enter passport numbers, SSNs, birth dates or financial details.'
            " Saved data is encrypted locally; the encryption key stays in your environment.</p>"
            '<form method="post" action="/profile">'
            f"{csrf()}{fields}"
            '<label for="confirmed_story">A statement you personally confirm as true</label>'
            f'<textarea id="confirmed_story" name="confirmed_story" rows="4">'
            f"{_text(story)}</textarea>"
            '<label><input name="consent" type="checkbox" value="yes" required>'
            " I consent to local encrypted storage of these details.</label>"
            '<button type="submit">Save encrypted profile</button></form></section>'
        )
        return _html("My profile", content)

    @app.post("/profile")
    async def save_profile(request: Request) -> Response:
        form = await request.form()
        if not safe_post(request, form):
            return HTMLResponse("Forbidden", status_code=403)
        if _field(form, "consent") != "yes" or not _field(form, "student_id"):
            return HTMLResponse("Consent and local profile ID are required", status_code=400)
        majors = tuple(item.strip() for item in _field(form, "majors").split(",") if item.strip())
        try:
            student = StudentProfile(
                student_id=_field(form, "student_id"),
                academic_level=_field(form, "academic_level") or None,
                visa_status=_field(form, "visa_status") or None,
                school=_field(form, "school") or None,
                majors=majors,
                gpa=float(_field(form, "gpa")) if _field(form, "gpa") else None,
                consent_to_store=True,
            )
            story = _field(form, "confirmed_story")
            evidence = (
                [
                    EvidenceItem(
                        id="local-story-1",
                        student_id=student.student_id,
                        statement=story,
                        confirmed_by_student=True,
                    )
                ]
                if story
                else []
            )
            bundle = ApplicantBundle(student=student, evidence=evidence)
            save_private(profile_path, bundle.model_dump(mode="json"))
        except (ValueError, RuntimeError):
            return HTMLResponse(
                "Please check the GPA, profile and encryption settings", status_code=400
            )
        return RedirectResponse("/", status_code=303)

    @app.get("/sources", response_class=HTMLResponse)
    async def sources(request: Request) -> Response:
        denied = gate(request)
        if denied:
            return denied
        term = (request.query_params.get("q") or "").strip().casefold()[:80]
        data = json.loads(sources_path.read_text(encoding="utf-8"))
        entries = data.get("sources", [])
        cards = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            url = str(entry.get("url", ""))
            kind = str(entry.get("kind", ""))
            status = str(entry.get("status", "candidate_unreviewed_terms"))
            if term not in (url + " " + kind).casefold():
                continue
            parts = urlsplit(url)
            if (
                parts.scheme != "https"
                or not parts.hostname
                or parts.username
                or parts.password
                or parts.port not in (None, 443)
            ):
                continue
            cards.append(
                '<article class="panel"><span class="pill">Unverified source</span>'
                f'<h2>{_text(parts.hostname)}</h2><p class="note">{_text(kind)}'
                f" · {_text(status)}</p><p>{_text(parts.path)}</p>"
                f'<a href="{_text(url)}" target="_blank" rel="noopener noreferrer">'
                "Open official source website</a></article>"
            )
        intro = (
            "<h1>Explore scholarship sources</h1>"
            '<p class="lead">Browse publicly listed institutional sites. They are '
            "NOT verified individual awards and are not matched to your F-1 eligibility.</p>"
            '<form method="get" action="/sources">'
            f'<label for="q">Search source or institution</label><input id="q" '
            f'name="q" value="{_text(term)}" placeholder="e.g. pcc.edu">'
            '<button type="submit">Search sources</button></form>'
        )
        return _html("Scholarship sources", intro + "".join(cards))

    @app.get("/my-sources", response_class=HTMLResponse)
    async def my_sources(request: Request) -> Response:
        denied = gate(request)
        if denied:
            return denied
        query = (request.query_params.get("q") or "").strip()[:80]
        awards = summarize_awards(research_store, search=query)
        cards: list[str] = []
        for award in awards:
            evidence = "".join(
                "<li><strong>"
                + _text(item["field"])
                + "</strong>: "
                + _text(item["quote"])
                + " (unverified)</li>"
                for item in award["candidates"]
            )
            checks = "".join("<li>" + _text(item) + "</li>" for item in award["review_queue"])
            cards.append(
                '<article class="panel"><span class="pill">NEEDS_VERIFICATION</span>'
                f"<h2>{_text(award['title'])}</h2>"
                f'<p><a href="{_text(award["source_url"])}" '
                'target="_blank" rel="noopener noreferrer">Open source in browser</a></p>'
                f'<p class="note">Pasted text · SHA-256: {_text(award["content_hash"])}</p>'
                "<details><summary>Candidate quotes (not verified rules)</summary>"
                f"<ul>{evidence or '<li>No rules extracted</li>'}</ul>"
                "</details><details><summary>Human verification checklist</summary>"
                f"<ul>{checks}</ul></details>"
                '<p class="note">NOT_SUBMITTED · No eligibility claim or receipt</p>'
                "</article>"
            )
        content = (
            "<h1>My scholarship research</h1>"
            '<p class="lead">Paste text from an individual scholarship page you are '
            "allowed to use. We encrypt the text and extract candidate evidence only. "
            "No URL fetching or automatic F-1 eligibility decisions.</p>"
            '<div class="warn">Every imported award remains NEEDS_VERIFICATION.</div>'
            '<section class="panel"><h2>Import an individual award</h2>'
            '<form method="post" action="/my-sources">'
            + csrf()
            + _input("Scholarship title", "title", required=True)
            + _input("Official HTTPS URL", "source_url", required=True)
            + '<label for="source_text">Text from public award page</label>'
            '<textarea id="source_text" name="source_text" rows="9" required '
            'maxlength="120000"></textarea>'
            '<button type="submit">Save encrypted source</button></form></section>'
            '<form method="get" action="/my-sources"><label for="q">Filter imported awards</label>'
            f'<input id="q" name="q" value="{_text(query)}">'
            '<button type="submit">Search</button></form>'
        )
        return _html("My researched awards", content + "".join(cards))

    @app.post("/my-sources")
    async def add_source(request: Request) -> Response:
        form = await request.form()
        if not safe_post(request, form):
            return HTMLResponse("Forbidden", status_code=403)
        try:
            import_award(
                research_store,
                title=_field(form, "title"),
                source_url=_field(form, "source_url"),
                source_text=_field(form, "source_text"),
            )
        except (OSError, ValueError, RuntimeError):
            return HTMLResponse(
                "Source rejected: check institutional URL and pasted page text",
                status_code=400,
            )
        return RedirectResponse("/my-sources", status_code=303)

    @app.post("/run")
    async def run_agents(request: Request) -> Response:
        form = await request.form()
        if not safe_post(request, form):
            return HTMLResponse("Forbidden", status_code=403)
        if not profile_path.is_file():
            return HTMLResponse("Save an encrypted student profile first", status_code=400)
        try:
            execute(profile_path, catalog_path, packets_path, today=date.today())
        except (OSError, ValueError, RuntimeError):
            return HTMLResponse(
                "Cannot prepare packets: verify local configuration", status_code=400
            )
        return RedirectResponse("/applications", status_code=303)

    @app.get("/applications", response_class=HTMLResponse)
    async def applications(request: Request) -> Response:
        denied = gate(request)
        if denied:
            return denied
        researched = summarize_awards(research_store)
        state = load_private(packets_path) if packets_path.is_file() else {"applications": []}
        cards: list[str] = []
        for award in researched:
            checks = "".join(
                "<li>" + _text(item) + "</li>" for item in award["review_queue"]
            )
            cards.append(
                '<article class="panel"><span class="pill">NEEDS_VERIFICATION</span>'
                f'<h2>{_text(award["title"])}</h2>'
                '<p class="note">Imported actual-page research, NOT_SUBMITTED. '
                'No eligibility verification or application packet yet.</p>'
                '<details><summary>Required human checks</summary>'
                f'<ul>{checks}</ul></details>'
                '<a href="/my-sources">Review original source and evidence</a>'
                '</article>'
            )
        for packet in state.get("applications", []):
            eligibility = str(packet.get("eligibility", "needs_verification"))
            reasons = "".join(
                f"<li>{_text(item.get('field'))}: {_text(item.get('code'))}</li>"
                for item in packet.get("reasons", [])
            )
            outline = "".join(f"<li>{_text(line)}</li>" for line in packet.get("outline", []))
            checks = "".join(
                f"<li>{_text(line)}</li>" for line in packet.get("required_checks", [])
            )
            content = (
                '<article class="panel"><span class="pill">'
                f"{_text(eligibility)}</span><h2>{_text(packet.get('title'))}</h2>"
                '<p class="note">Status: '
                f"{_text(packet.get('submission_status'))} · "
                f"Approved: {_text(packet.get('approved'))}</p>"
                "<details><summary>Evidence and reason codes</summary>"
                f"<ul>{reasons}</ul></details>"
                "<details><summary>Draft outline (student must review)</summary>"
                f"<ul>{outline}</ul></details>"
                "<details><summary>Before applying</summary>"
                f"<ul>{checks}</ul></details>"
                '<p class="note">A decision here is based on the local catalog. '
                "It is not proof of actual provider eligibility or submission.</p>"
                '<form method="post" action="/approve">'
                f"{csrf()}"
                f'<input type="hidden" name="packet_id" value="{_text(packet.get("id"))}">'
                f'<input type="hidden" name="packet_hash" '
                f'value="{_text(packet.get("packet_hash"))}">'
                '<label><input type="checkbox" name="student_confirmed" value="yes" required>'
                " I reviewed this exact packet for manual submission.</label>"
                '<button type="submit">Approve packet (does not submit)</button>'
                "</form></article>"
            )
            cards.append(content)
        prefix = (
            "<h1>Application packets</h1>"
            '<div class="warn"><strong>NOT SUBMITTED.</strong> This local demo uses '
            "a fictional catalog. Approval never sends any application to a provider.</div>"
        )
        if not cards:
            cards.append(
                '<section class="panel">No applications or imported awards yet. '
                'Add a real award in My researched awards or try the fictional demo.</section>'
            )
        return _html("Applications", prefix + "".join(cards))

    @app.post("/approve")
    async def approve_review(request: Request) -> Response:
        form = await request.form()
        if not safe_post(request, form):
            return HTMLResponse("Forbidden", status_code=403)
        try:
            approve(
                packets_path,
                packet_id=_field(form, "packet_id"),
                packet_hash=_field(form, "packet_hash"),
                student_confirmed=_field(form, "student_confirmed") == "yes",
            )
        except (OSError, ValueError, RuntimeError, PermissionError):
            return HTMLResponse(
                "Approval rejected: review the latest exact packet", status_code=400
            )
        return RedirectResponse("/applications", status_code=303)

    return app
