# ScholarOS v0.5 — Local Student Dashboard

**Implemented as a private, localhost-only browser UI.** It does not host a public service and does not submit any scholarship application on your behalf.

## Install

Python 3.11+ is required:

```bash
git clone https://github.com/nguyenbui1105/scholaros.git
cd scholaros
python -m pip install -e ".[web]"
```

Set a **private Fernet encryption key** before launching the app. Generate once; save it in your password manager. If the key is lost, existing encrypted files cannot be recovered.

macOS/Linux:

```bash
export SCHOLAROS_FERNET_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
scholaros web
```

Windows PowerShell:

```powershell
$env:SCHOLAROS_FERNET_KEY = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
scholaros web
```

Open `http://127.0.0.1:8765/unlock`. Enter the randomly generated access code printed by `scholaros web` in your terminal. Never post your code or encryption key publicly.

## Screens

1. **Dashboard:** one place to navigate the student flow. Always labels the catalog as fictional.
2. **My profile:** asks for a nonidentifying local ID, school, academic level, visa category, majors, optional GPA (0–4 scale), and a truthful first-person statement. Requires explicit consent to locally encrypted storage. Does not ask for passport/SSN/financial records.
3. **Scholarship sources:** searchable directory of publicly discoverable institutional sources from `examples/source_discovery_seeds.json`. Links are marked `candidate_unreviewed_terms`, not as verified scholarships or F-1 eligibility. Opening the link navigates your browser to the source; the app does not crawl it.
4. **Run agents (demo):** uses the existing in-process deterministic 7-role agent coordinator to generate a review packet from `examples/agent_demo_catalog.json`. That sample award is **fictional** and is not a real application opportunity.
5. **Applications:** inspect status, uncertainty reason codes, evidence-only outline, checklist and submit an explicit **packet approval** bound to the exact SHA-256 digest. Approval changes only your encrypted local record. Status remains **NOT_SUBMITTED**.

## Security boundary

- Server binds to `127.0.0.1` only. There is no `--host` option to expose it on the network.
- Login uses a high-entropy ephemeral access code printed in the terminal, an HttpOnly + SameSite=Strict session cookie, Host allowlist, CSRF checks and Origin/Fetch-Site checks for POST requests.
- CSP blocks remote scripts, frames and external assets. User-supplied values are HTML-escaped. No third-party analytics or tracking.
- Both profile and packet workspace are encrypted at rest with the existing Fernet mechanism. No plaintext profile file is written by the UI.
- This is not a production multi-user security audit: avoid reverse proxies/tunnels; key rotation, account recovery, OS-level access control, hardened backups and penetration testing are not implemented.
- Do not store genuine visa numbers, sensitive IDs, bank information or passports in the prototype.
- No authorized submission transport or official source verification is present. A program page or source directory entry does not imply that an international student is eligible.

## Test

```bash
pip install -e ".[dev]"
pytest -q tests/test_webui.py
ruff check src tests
ruff format --check src tests
mypy --strict src/
```

Web dependencies are optional for CLI-only installs. The web UI test suite uses FastAPI TestClient and synthetic fixtures; no network or external AI API keys required.

## Next milestone

Replace synthetic award catalog with reviewed individual-award records and per-requirement provenance, add a transparent human verification workflow, real deadline validation, and accessible essay/packet editing. A real provider submission adapter requires official terms/permission, explicit applicant approval of the exact destination and packet, and independently verified receipt tracking. No CAPTCHA circumvention.

## Verified offline test result

The feature branch passed **183 tests** with **86.24% statement coverage** in [CI 45000116305](https://github.com/nguyenbui1105/scholaros/actions/runs/45000116305). This verifies the localhost workflow with synthetic fixtures, **not** a real-provider scholarship search, eligibility outcome, or application submission.
