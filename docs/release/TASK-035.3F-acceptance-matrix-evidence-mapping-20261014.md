# TASK-035.3F — current independent-gate matrix mapping

Date: 2026-10-14. This is a **dated addendum** to the 80-row
`TASK-035.2-acceptance-traceability-matrix-20261013.md`, not a rewrite of its
2026-10-13 observations. `PASS` below applies only to the explicitly named
sub-check, never to a parent row requiring live/owner evidence. Statuses use
the parent matrix vocabulary: PASS, FAIL, NOT_RUN, EVIDENCE_GAP, CONFLICT,
DEFERRAL_PROPOSED. Evidence locations: **F** =
`TASK-035.3F-frontend-qualification-20261014.md`; **S** =
`TASK-035.3F-backend-build-security-verification-20261014.md`; **C** =
`TASK-035.3F-ci-observability-review-20261014.md`; **D** =
`TASK-035.3D-affected-criteria-analysis-20261014.md`; **E** =
`TASK-035.3E-bounded-context-admission-investigation-20261014.md`.

| ID | Previous matrix status | Verification / actual observed result | Evidence | Current effective status | Remaining gap / required next action |
| --- | --- | --- | --- | --- | --- |
| B01A | NOT_RUN | Host 3.11 non-red unit suite 1423 PASS / 3 XFAIL; source app compiles. | S | **EVIDENCE_GAP** | Candidate 3.12 and full red safety contracts not green; qualify a new versioned candidate only after safety remediation. |
| B05 | NOT_RUN | Auth/password/refresh unit files included in passing host suite; no live auth transaction. | S | **EVIDENCE_GAP** | Isolated candidate login/refresh/logout/inactive-user flow. |
| B06 | EVIDENCE_GAP | Role/permission unit files passed; no current full role/department integration matrix. | S | **EVIDENCE_GAP** | Isolated RBAC matrix including revocation and inactive users. |
| B16 | EVIDENCE_GAP | Retrieval/context source reviewed; 035.3E synthetic admission 4/4 intended exclusions fail. No current channel-score runtime trace. | E,S | **EVIDENCE_GAP** | Keep distinct application context-admission safety blocker; do not infer retrieval permission defect or invent a score cutoff. |
| B19 | PASS (historical V2 set) | No new RAG runtime run; 035.3B STAFF unsupported-answer gate remains failed and 035.3E red contracts remain. | D,E | **FAIL for current RC safe no-answer; historical PASS retained** | Separate generic safety correction plus new candidate positive/negative runtime gate. No deferral. |
| B21 | PASS (historical V2 set) | No new citation runtime run; failed STAFF citation had valid identity but no question-material support. | D,E | **FAIL for current RC question-materiality; historical PASS retained** | Prove material cited answer to question on new candidate; identity validation remains necessary. |
| B22 | EVIDENCE_GAP | Host citation/permission unit tests pass; no current cross-user/revocation runtime. | S,D | **EVIDENCE_GAP** | Isolated permission revalidation/history persistence gate. |
| B26 | EVIDENCE_GAP | CI workflow reviewed; backend gates configured; frontend CI and current dirty-tree run absent. | C,S | **EVIDENCE_GAP** | Versioned same-source CI including frontend/security/dependency controls. |
| B27 | NOT_RUN | Bounded security scan and unit suite passed; current production-like security smoke not run. | S | **EVIDENCE_GAP** | Isolated rate-limit/CORS/host/upload/errors and permission gate. |
| P02 | EVIDENCE_GAP | `SecretStr`, `_FILE`, redaction and production validation inspected; bounded scan passed. | S | **EVIDENCE_GAP** | Current candidate privacy/startup/failure-path tests and fresh secret scan. |
| P10 | NOT_RUN | Typed frontend typecheck/build PASS; no live frontend-backend operation. | F | **EVIDENCE_GAP** | Live isolated same-source candidate API compatibility. |
| P11 | NOT_RUN | Mocked Chromium Admin/Staff navigation PASS; backend RBAC not exercised. | F | **EVIDENCE_GAP** | Real role/session navigation with backend enforcement. |
| P12 | EVIDENCE_GAP | Mocked admin user/department E2E and frontend units PASS; no live upload/permissions/feedback/audit flow. | F | **EVIDENCE_GAP** | Isolated end-to-end core workflows and READY state. |
| P13 | EVIDENCE_GAP | Mocked SSE/citation browser test PASS; no live stream, source materiality or safe-no-answer verification. | F,D | **EVIDENCE_GAP** | Live candidate SSE/nonstream parity, citation and error gate after RAG safety fix. |
| P14 | NOT_RUN | Lint PASS with 7 warnings, typecheck PASS, Vitest 36/36, mocked Chromium 9/9, build PASS. No full accessibility audit. | F | **EVIDENCE_GAP** | Accessibility/keyboard review and current live primary workflow tests. Scoped source/mock sub-checks PASS only. |
| P22 | EVIDENCE_GAP | Existing external-transfer warnings inspected; no chosen production provider/residency approval. | S | **EVIDENCE_GAP** | Security/release owner decision for actual provider/data classes. |
| P27 | EVIDENCE_GAP | Logging redaction and observability unit tests passed; no current candidate log/trace stream. | S,C | **EVIDENCE_GAP** | Production-like safe log/trace and alert guidance gate. |
| P28 | NOT_RUN | Development, production and production-observability Compose `config --quiet` PASS; no build/up. | S | **EVIDENCE_GAP** | Approved production-like same-source startup/health/resource gate. |
| P29 | EVIDENCE_GAP | Nginx static headers/SSE/metrics block and disabled HTTPS example inspected. | S,C | **EVIDENCE_GAP** | Real certificate-backed TLS/proxy/access checks. |
| P30 | EVIDENCE_GAP | Metrics/request-ID implementation and scrape/dashboard config inspected; unit tests passed. | S,C | **EVIDENCE_GAP** | Live non-disclosure scrape/log review, retention and alerting. |
| R03 | CONFLICT | README/checklist/SECURITY historical status, migration and TLS passages remain inconsistent with current state. | S | **CONFLICT** | Later owner-reviewed documentation reconciliation; no silent contract rewrite. |
| R05 | FAIL | Active V2 API image `1f057785...` and worker `1e19725c...` remain skewed; failed 035.3B candidate is not promotable. | S,D | **FAIL** | New same-source safe candidate and approved promotion path after safety closure. |
| R06 | EVIDENCE_GAP | Git remains dirty/uncommitted; local build does not version accepted H5.2 source. | S | **EVIDENCE_GAP** | Reviewed commit/provenance plan under separate authorization. |
| R07 | EVIDENCE_GAP | New local build output/report; historical key evidence remains ignored/local. | F,S | **EVIDENCE_GAP** | Durable protected/off-host evidence preservation with checksum verification. |
| R09 | EVIDENCE_GAP | Compose and local dependencies inspectable; no immutable base/wheel/model-byte clean-room rebuild. | S,C | **EVIDENCE_GAP** | Authorized reproducibility proof and SBOM/lock/image export. |
| R13 | CONFLICT | No new RC approval; old `v1.0.0-rc1` freeze wording remains historical/unsupported. | S,D | **CONFLICT** | Later release-owner documentation decision; no tag creation. |
| R14 | CONFLICT | Checklist cites `20260722_0009`, README cites older head; established V2/source head `20260822_0011`. | S | **CONFLICT** | Later migration/version doc reconciliation. |
| R15 | EVIDENCE_GAP | Production Compose parses; Nginx active config is HTTP 8080, HTTPS example disabled. | S,C | **EVIDENCE_GAP** | Approved production TLS certificate/handshake/security-header gate. |
| R18 | EVIDENCE_GAP (historical matrix) | Bounded scan/host unit PASS; independent permission-aware unsupported-answer gate still FAIL. | S,D,E | **FAIL for candidate answer-safety subclaim; EVIDENCE_GAP for remaining security controls** | Safety correction plus current candidate security/log/RBAC suite. |
| R19 | NOT_RUN | Source/mock frontend type/lint/unit/build/Chromium passed; no live candidate frontend. | F | **EVIDENCE_GAP** | Same-source live E2E and accessibility audit. |
| R20 | DEFERRAL_PROPOSED | Plaintext/PII/retention/malware limitations remain documented; no owner approval. | S | **DEFERRAL_PROPOSED** | Security/privacy/release decision or remediation. Approved deferrals remain zero. |

Other matrix rows retain their prior dated status unless separately qualified
by 035.3D. In particular, this checkpoint does not promote B19/B21, R01/R02,
the current unsupported-answer safety gate, off-host DR, historical Celery
accounting, rollback, performance, or production TLS to PASS. No deferred
criterion was approved. Static evidence does not substitute for a live check.
