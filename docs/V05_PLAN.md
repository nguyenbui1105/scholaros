# ScholarOS v0.5 — Local Student Experience MVP

## Product decision
Build a **localhost-only** student-facing web interface on top of the existing encrypted workspace, not a publicly hosted SaaS. It provides an onboarding wizard, a list of *unreviewed* institutional scholarship-source links, a visible pipeline for the deterministic agent roles, and packet review/approval.

The current repository does not contain an independently vetted real scholarship catalog. Accordingly the UI **must not** imply that its 11 institutional source links are 11 eligible awards, and it must label its default award fixture clearly as fictional. The UI will never automatically submit or claim a submission receipt.

## Engineering and security phases
1. **Red tests first**: login required; forged Origin/CSRF rejected; no private fields exposed before authorization; HTML injection escaped; no network; no local profile saved without consent/valid Fernet key; demo matching, packet details, exact hash-bound approval, NO submission.
2. **Optional web dependency**: FastAPI+Uvicorn+python-multipart, installed through `.[web]` or `.[dev]`; no API keys/network required.
3. **Local browser server**: `scholaros web` binds only `127.0.0.1`; a high-entropy startup access code is shown in the terminal; cookie HttpOnly+SameSite Strict, trusted Host checking, Origin/CSRF checked on POST. No tracking, CDN, remote scripts or external API access.
4. **Real screens**: onboarding, source directory/search with evidence status, 7-role execution, readable packet dashboard, student exact-packet approval (only for manual submission). All user content HTML-escaped.
5. **Verification**: run Ruff lint/format, `mypy --strict src/`, pytest+coverage >=85%, Python 3.11/3.12, pip-audit, Gitleaks. Keep `main` green; update README/STATUS/SECURITY and clearly distinguish implemented features and gaps.

## Deferred for the next milestone
- Real rights-cleared, human-reviewed per-award catalog and live deadline checks
- Provider-authorized submission adapters with individual consent and verified receipts
- Hosted authentication, encrypted backups/key rotation, rate limiting and accessibility review
- Semantic essay verification, deployed persistent agents or any guaranteed scholarship result

## Acceptance
Fresh clone `pip install -e ".[web]"` + `SCHOLAROS_FERNET_KEY` + `scholaros web` opens an actual browser interface; complete synthetic workflow from form to packet review/approval, all off-network; red-to-green tests; no unsafe live submission.
