# v0.8 — Local scholarship discovery inbox (offline MVP)

**Scope:** A local browser workflow for collecting *candidate links* from HTML the user already has permission to access. It neither fetches a webpage nor verifies an institution, scholarship, citizenship/visa requirements or provider terms. It does not send applications.

## How to use

1. Pull the latest code and run `scholaros web` with your existing encrypted Fernet key (see [Web UI](WEB_UI.md)).
2. Unlock the dashboard and open **Discover leads**.
3. Visit a public scholarship index using your normal browser and confirm that you may use its content. Copy its HTML source and the index's official HTTPS address.
4. Paste the index URL and its HTML. ScholarOS finds **same-origin** scholarship-like links; duplicate links, logins, external hosts and PDF files are excluded. The source HTML is *not retained* as a plaintext file.
5. Browse/filter the **UNREVIEWED_CANDIDATE** inbox. Each lead retains its original index URL and the SHA-256 digest of the index HTML. The inbox is stored encrypted as `.scholaros/discovery_leads.enc`.
6. Open a lead and inspect the current official individual award page yourself. Paste the source text and title into the inline form to create an encrypted award snapshot under **My researched awards**.
7. If useful, continue to **Preliminary matching**, where you must personally review and cite the original F-1, GPA and deadline requirements before tentative comparisons.

## Scope and limitations

- **No crawler, automatic HTTP retrieval, live website verification, actual institutional authentication or guaranteed 50–100-page collection** is delivered in v0.8. `discover_links` parses provided HTML, not internet search results.
- Discovered links have a **plausible** institutional hostname only, not a verified endorsement. The same-origin filter is exact-host, HTTPS, no credentials or odd ports, and excludes typical login/application paths.
- An index can include generic category pages or outdated entries. A candidate is not necessarily an individual scholarship.
- Source intake only supports text from sources the user has the right to use. It is not permission to redistribute, copy restricted pages or bypass robots/terms.
- All discovered leads remain `UNREVIEWED_CANDIDATE`; promoted source snapshots remain `needs_verification`; applications remain `NOT_SUBMITTED`. The demo agent runner remains fictional, not attached to this discovery inbox.
- The locally encrypted inbox must be opened with the same Fernet key; no recovery, key rotation or secure cloud backup is provided.
- Controls include local access-code authentication, CSRF/Origin validation for POST, HTML escaping, bounded input size, path filtering, deduplication and a 250-lead cap. No browser tunnels or production hosting.

## Next milestone — actual discovery and verification

Separate explicit source-use authorization, per-provider robots checks, controlled fetch, signed/reviewed provider catalogs, source freshness, hard eligibility rules (citizenship, school, GPA, major, deadlines), measured precision/false-eligible rates and per-scholarship application packets. Supported portal submissions require per-destination consent and genuine external receipts. None of these can be inferred from a discovered URL.
