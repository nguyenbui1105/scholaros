# ScholarOS Assisted Application Workspace

## What works now

After installing `scholaros` and setting `SCHOLAROS_FERNET_KEY`, students can enter a minimal profile once, encrypt it locally, run deterministic specialist-agent roles against a **local catalog of reviewed individual award cases**, inspect the generated checklist/outline, and explicitly approve an immutable packet hash for *manual* submission.

The workflow currently coordinates seven logical roles:

1. Source researcher: verifies whether the individual award has a named human source reviewer; source strings remain untrusted.
2. Eligibility guardian: evaluates all source-anchored rule quotations, reports mismatches and unknowns separately.
3. AI policy officer: only allows an outline if a positive source-backed AI-use policy was reviewed; default is none.
4. Narrative coach: references only student-confirmed statements and does not invent achievements.
5. Packet compiler: builds a version-hashed application checklist, not a fabricated submission receipt.
6. Strategy ranker: ranks only source-reviewed ELIGIBLE cases.
7. Submission coordinator: **does not send**. It returns NOT_SUBMITTED and requires an exact-packet approval before any future provider-specific API adapter could be used.

These are deterministic, modular agent roles (not independent persistent agents or seven separately deployed LLMs). The official scholarship catalog remains **incomplete**; the demo catalog is fictional.

## Run locally

Install Python 3.11+ and dependencies:

```bash
python -m pip install -e ".[dev]"
# macOS/Linux:
export SCHOLAROS_FERNET_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
# Keep the key privately in a password manager; never commit it or paste it into GitHub.
scholaros onboard --out .scholaros/profile.enc
scholaros autopilot --vault .scholaros/profile.enc \
  --catalog examples/agent_demo_catalog.json \
  --out .scholaros/applications.enc --json
scholaros workspace --file .scholaros/applications.enc --json
# Deliberately show private contents ONLY if requested:
scholaros workspace --file .scholaros/applications.enc --reveal --json
```

The interactive `onboard` command requests a local profile ID, school, visa category, level, majors, optional GPA, and one confirmed first-person statement. It does not request SSNs, passport numbers, immigration documents, birth dates, or banking details. It requires explicit local encryption consent. An optional `--profile-json` import is available for users who already have a plaintext JSON profile, but **delete that plaintext file yourself** after import.

To reproduce the fictional test without typing:

```bash
scholaros onboard --profile-json examples/agent_demo_profile.json --out .scholaros/profile.enc
scholaros autopilot --today 2026-11-20 --json
```

The default catalog is *fictional*, with `fixture_only=true`. Successful matching of this fixture is **not proof of eligibility for any real scholarship**.

## Approve exact packet for manual submission

Inspect `scholaros workspace --json`, then supply the exact packet ID and hash:

```bash
scholaros approve-packet --packet-id fictional-stem --hash <64-character-hash> --yes --json
```

Approval is recorded only in the encrypted local workspace; no portal is contacted and no application receipt is invented. Any edit changes the packet hash and invalidates approval. No real-provider submission adapters ship with this repository yet.

## Real-use limitations and prerequisites

- A program landing page does **not** establish criteria for an individual award. For real catalog entries, manually verify source authenticity, every constraint, other conditions, and the scholarship's AI-writing policies. Supplying a reviewer string by itself is *not* independent authentication.
- A local encrypted file is not a production multi-user vault. Key loss makes it unreadable; key rotation, backups, web auth, tenant isolation and deletion of external copies are not provided.
- Essay writing is **outline-only** under explicit permission; student-authored final essays and human review remain mandatory. Unknown AI policy prohibits writing assistance.
- Automatic external application submission across portals is **not implemented**; site terms, authentication, accessibility, explicit per-packet student approval, audited permitted provider APIs and verified submission receipts are needed.
- No site login scraping, CAPTCHA/anti-bot bypass or guarantee of scholarship awards. This tool is not legal, immigration, or financial-aid advice.
