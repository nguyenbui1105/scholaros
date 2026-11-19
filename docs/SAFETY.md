# Safety, research ethics and limitations

- **Authenticity:** never invent GPA, visa status, financial hardship, awards, quotes or references; all first-person claims belong to the student.
- **Source integrity:** a quote/hash-backed fixture is stronger than a bare boolean but does not independently authenticate an external provider. Verify real official pages and dates manually.
- **Eligibility:** missing applicant data, unknown requirements or stale sources block eligibility; an explicit mismatch may be ineligible only when backed by current corresponding rule text.
- **AI-use rules:** policy `unknown`/`prohibited` forbids AI writing; `editing_only` permits editing help; disclosure-required needs user approval before drafting. Validate specific provider rules before using any live writing capability.
- **Review limits:** literal claim matching rejects some supported paraphrases and may miss subtle implication/hallucination; independent human review is necessary.
- **Application operations:** this beta creates packets and checklists only. It does not log in, submit, bypass CAPTCHA, or perform anti-bot workarounds.
- **Privacy:** no real student PII in git or fixtures. The SQLite vault refuses plaintext unless local-only override explicitly enabled; encryption lacks key rotation, secure backup erasure, login and tenant isolation.
- **Scraping:** live fetch is disabled by default, checks robots and has conservative rate limits, but is not a license to scrape any provider.
- **Metrics:** a synthetic 36-pair benchmark is not a real-world scholarship award prediction. No statistical acceptance rate is offered.
- **Legal disclaimer:** not legal, immigration, or financial-aid advice. Scholarships and awards are never guaranteed.

See [threat model](THREAT_MODEL.md) and [evaluation](EVALUATION.md).
