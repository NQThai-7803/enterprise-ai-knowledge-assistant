# TASK-035.3G — frontend delivery qualification summary

Date: 2026-10-14. **TASK-035.3G COMPLETED as an independent verification
checkpoint with new frontend accessibility failures; TASK-035 remains IN
PROGRESS and RC remains NO-GO.** No production source/config, backend,
database, Redis, candidate, dependency lock or running service was changed.

## Protected baseline and commands

Git HEAD `04ebd73aae737414fb591fe2e8b2c286134cdcd8`; accepted H5.2
source and 035.3F docs/evidence remain dirty/uncommitted or local/ignored.
Package-lock SHA-256
`1fdf9b6d438cedc1f4027a43195407bcc1f2363f4acac50862f3403c6aa195d5`;
035.3B `permission-safety.json` SHA-256
`b6e0f415dee409be55786fb4788cf9888d06890e0cfe684444013a5a1196714f`.
Protected `app/services/grounded_answer_service.py` SHA-256 remains
`4c9d4c648bbcef30a35c4e2ca01fad0093ed0e7a8aebb777dc78b478b345c919`;
tracked `frontend/src/components/ui/ConfirmDialog.tsx` is
`3a6a708ef3d51bbba7cc0769ff940e78db2f756040be69f5f3557e3e5b89d428`.
Active V2 API `9d510d8b8027`, Redis `db2961fc9413`, worker
`2afc4af27fe5`, PG `1a5a658a2ef2` were healthy with unchanged identities
before/after local tests, all with restart count 0. API image ID
`sha256:1f057785bd8cacb68aa8573e3aa12e29a23c37692e0ad045997770d4adf2648e`
and worker image ID
`sha256:1e19725cdd8929d30311fd5dbf4605fe7279d22d3a4fe7823046e44ce13aa570`
remain distinct. No protected service or data was targeted. Node was
`v24.14.0`, npm `11.9.0`; existing installed dependencies were used.

| Check | Actual result | Limitation |
| --- | --- | --- |
| `npm run typecheck` | PASS | Host/local source only. |
| `npm run lint` | PASS, 0 errors, **7 warnings** | Hook dependency/incompatible-library warnings retained. |
| `npm run test -- --run` | PASS, 36/36, 7 files | First sandbox attempt had temp-rename EPERM before tests; authorized unsandboxed rerun passed. |
| `npm run test:e2e` | **11 PASS / 2 FAIL**, 13 mocked Chromium tests | Both failures are new confirmation-dialog keyboard/focus checks; original 9/9 passed. No V2/live backend. |
| `npm run build -- --outDir ../artifacts/task-035-3g-20261014/frontend-dist` | PASS, Vite 8.1.5, 1,978 modules | Local default API origin, source map emitted; output ignored/local. |
| Repository-wide Ruff check/format | **FAIL**: 24 check errors / 3 unformatted files | Only scratch traces and one 3C.2F harness; no automatic disposition. |

See the API-origin/bundle, accessibility, delivery-contract and source-hygiene
reports of this phase for exact paths, hashes, observations and limits.

## TASK-035 acceptance mapping (dated addendum)

The 2026-10-13 035.2 matrix and 035.3F mapping remain historical snapshots.
Statuses below describe the **current effective criterion**, not a retroactive
rewrite of those records. All checks here were LOCAL source/build or mocked
Chromium, never a live same-source candidate.

| Criterion | Previous effective status | Check/environment/result | Evidence | Current justified status / remaining limit |
| --- | --- | --- | --- | --- |
| P10 typed API/local operation | EVIDENCE_GAP | Typecheck/build PASS; static API path/shape comparison LOCAL | delivery-contract report | **EVIDENCE_GAP**: no live frontend↔backend operation. |
| P11 role-aware navigation | EVIDENCE_GAP | Existing Admin/Staff mocked Chromium PASS | accessibility report | **EVIDENCE_GAP**: backend RBAC/current session untested. |
| P12 core workflows | EVIDENCE_GAP | Existing mocked Admin UI PASS; document client/status static review | delivery-contract report | **EVIDENCE_GAP**: no live upload→READY/permission/feedback/audit. |
| P13 chat/SSE/citation/errors | EVIDENCE_GAP | Existing mocked SSE/citation PASS; static event/schema review | delivery-contract report | **EVIDENCE_GAP**: no live stream/materiality/safe error; RAG safety still FAIL. |
| P14 reusable states/tests/accessible controls | EVIDENCE_GAP | Typecheck/lint/Vitest/build PASS; 13 mocked browser tests 11 PASS/2 FAIL | accessibility report | **FAIL for dialog keyboard accessibility**; other workflow/manual checks remain gaps. |
| R03 current docs/secrets | CONFLICT | Local bundle marker scan and origin review | API-origin report | **CONFLICT** unchanged; no comprehensive secret or docs reconciliation. |
| R07 durable evidence | EVIDENCE_GAP | New build/test traces local and ignored | this summary | **EVIDENCE_GAP**: no versioned/off-host proof. |
| R19 frontend candidate verification | EVIDENCE_GAP | Static/mock suite with dialog failures | accessibility + delivery reports | **FAIL for accessibility sub-check; EVIDENCE_GAP for live candidate integration**. |

B19/B21 and R18 unsupported-answer safety remain current RC **FAIL**;
R05 active API/worker skew remains **FAIL/unresolved**. No release deferral was
approved (0). No unrelated matrix criterion is promoted. The failed 035.3B
candidate remains preserved and is not eligible for promotion.

## Next gate

Separately authorize a generic confirmation-dialog focus/Escape correction
with focused keyboard regressions, then rerun mocked accessibility. Decide
production API-origin/source-map policy and source-hygiene disposition before
deploying a frontend. A new same-source candidate, RAG answer-safety closure,
live E2E, full accessibility/manual checks, and remaining release/owner gates
are still required. No RC sign-off or live-E2E PASS is claimed.
