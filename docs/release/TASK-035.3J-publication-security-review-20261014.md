# TASK-035.3J — offline source-publication preflight

Scope: all 553 paths proposed for source, test/tooling or release-docs Git
inclusion, plus separate owner-review paths, without publishing or moving
bytes. All 495 selected originals from 035.3I still match their prior
manifest. The custom offline source security scan passed; this checkpoint
rechecked all 553 selected path names and high-signal private-key/AWS/GitHub/
OpenAI token markers without printing values. Unexpected sensitive-name
matches: **0**; high-signal marker-file matches: **0**.

| Category | Finding / decision |
| --- | --- |
| Environment files | Only `.env.example`, `.env.production.example`, and `frontend/.env.example` are in the 495-file selection. Real `.env` and `.env.task035.production` remain ignored/excluded. Example secret/password entries were previously checked as empty or placeholders; production-example Redis URLs had no embedded userinfo. Manual template review still required. |
| Credentials, access tokens, private keys | No high-signal `BEGIN … PRIVATE KEY`, AWS access-key, GitHub PAT or OpenAI-style key marker matched selected text files in the bounded offline scan. This does **not** rule out other secret formats or embedded document content. CI contains explicit synthetic local test credentials; their intent must remain clear. |
| Dumps, PDFs, personal user data, model bytes | No database dump, private UAT PDF, model weight/cache, or `data/`, `.backups/`, `uat/` path is in the source tar. Those categories remain access-controlled; runtime manifests and raw logs require privacy review before any sharing. |
| Generated output / binaries | `artifacts/`, `.venv/`, frontend `node_modules/`, `dist/`, caches and coverage are excluded. The tracked legacy zip/PNG and nested Gitlink are **review required**, not approved for source publication by this scan. |
| Research/release reports | Experimental traces may contain runtime identifiers/text. Older `docs/release/` reports and UAT scripts/overlays are **review required** for confidential answers, person names, paths, credentials and license obligations before any Git commit or external publication. |

This is a limited local name/pattern/custom-script scan, not SAST, complete
secret scanning, malware scanning, license clearance, dependency advisory
review, image scanning, or public-release authorization. The proposed Git
inclusion set is **not yet certified free of unauthorized secrets**. A human
review of the exact future staged diff and binaries is mandatory. No private
evidence was transferred.
