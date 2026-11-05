# TASK-035.3H — confirmation dialog keyboard remediation

Date: 2026-10-14 (Asia/Saigon). **COMPLETED for the authorized local
frontend correction and mock regression scope; TASK-035 remains IN PROGRESS,
RC NO-GO.** Historical 035.3G 11/13 result remains unchanged in its report.
No backend, Docker image, active V2 service, database, Redis, dependency,
source-map policy, API-origin configuration, or release candidate was changed.

## Reproduction and first origin

Before application edits, `npm run test:e2e -- --grep 'confirmation dialog
receives focus|Escape dismisses confirmation' --workers=1` reproduced both
existing Chromium failures (0/2 PASS). The first sandboxed attempts could
not reach the local Vite socket; an approved unsandboxed local/mock rerun
completed. The new pre-fix browser trace recorded:

- On open, `document.activeElement` remained the background **Deactivate**
  button, outside `role="dialog"` (`aria-modal="true"`).
- Shift+Tab moved to the background **Edit** button; Tab moved back to the
  background Deactivate button. The dialog had no `aria-describedby`.
- Escape left the dialog open. Clicking Cancel closed it but left focus on
  `body`. After successful mocked deactivation replaced the trigger, focus
  was also on `body`.
- Focused pre-fix Vitest: 1/3 PASS, 2 FAIL (description/focus and pending
  focus). The prior successful click-through test alone did not establish
  keyboard behavior.

The first defect boundary was the shared `ConfirmDialog.tsx` component, not
the Admin user API or the Playwright mock. It rendered the modal markup and
buttons but supplied no focus lifecycle, Tab containment, Escape handling,
description association or restoration. Callers already controlled open state
and close-on-success; that confirmation contract was retained.
The [W3C WAI-ARIA modal dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
describes initial in-dialog focus, contained Tab/Shift+Tab navigation,
Escape dismissal, and logical focus return. Starting on Cancel also follows
its guidance to prefer the least destructive action for hard-to-reverse
confirmation. The existing app's `loading` lock remains an intentional
exception to Escape dismissal while an operation is pending.

## Narrow correction

Only production file changed: `frontend/src/components/ui/ConfirmDialog.tsx`.
SHA-256 before
`3a6a708ef3d51bbba7cc0769ff940e78db2f756040be69f5f3557e3e5b89d428`;
after
`1f0f1ef7dc8ae7d1decaed33aec3e2d8bdd9e72d88800e4570c9fc42e20991c7`.

The dialog now focuses the first enabled action (Cancel) on opening, keeps
Tab/Shift+Tab within its enabled actions, redirects attempted outside focus
back inside, associates its heading and message using stable unique IDs, and
restores focus to the live trigger on close. If the trigger has been removed,
it selects a live control in the former container or current main content
instead of focusing a detached node. Restoration is deferred to a microtask
after DOM commit, and the focus listener is removed on close/unmount.
During `loading`, both existing buttons remain disabled; the dialog surface
holds focus, Escape/Tab cannot bypass the pending action, and focus returns
to an enabled action if loading ends without closure. Escape closes only when
not loading. Confirmation still invokes the caller exactly once and does
not auto-close before caller success; mouse Cancel/Confirm behavior remains.
No new framework, dependency, global keyboard listener, backend branch,
permission rule or visual redesign was introduced.

Test files: new `frontend/src/components/ui/ConfirmDialog.test.tsx`
(SHA-256 `6a2760e63906cbd01e530d654efcb28707fdbfdeb2a07cd697dff7d787a3b79d`),
and refined existing untracked 035.3G
`frontend/src/test/e2e/accessibility.qualification.spec.ts` (before
`c768ca17468ef60b50283a2fd0a1728327f86d2c43e6fbb63f5d8f3ea25e7382`,
after `f05bd9018f2e560bfcba739f49b35045c79ad1b5fefe3a2b816907fad1c00953`).
Browser assertions were strengthened, not disabled or weakened. They cover
both original failures, both Tab directions, attempted background focus,
Cancel/Escape restoration, repeat open/close, accessible name/description,
and a successful action whose trigger is replaced. Component tests cover
pending transition/initial pending lock, disabled actions, and no premature
auto-close. Existing Admin/Staff role-aware tests remain in the full run.

## Verification

| Gate | Result |
| --- | --- |
| Focused ConfirmDialog Vitest | 4/4 PASS |
| Focused accessibility Chromium | 6/6 PASS, including both formerly failing tests |
| Full `npm run typecheck` | PASS |
| Full `npm run lint` | PASS, zero errors, same seven unrelated warnings in ChatPage/DocumentPermissionsPage/DocumentUploadPage |
| Full `npm run test -- --run` | 40/40 PASS across eight files (previous baseline 36/36) |
| Full `npm run test:e2e` | 15/15 mocked Chromium PASS (previous baseline 11/13; original nine remain PASS) |
| Isolated build | PASS, Vite 8.1.5, 1,978 modules, output `artifacts/task-035-3h-20261014/frontend-dist/`; JS 412.49 kB, CSS 23.83 kB, map 1,618.90 kB |
| `git diff --check` on tracked changes | PASS |

The isolated JS SHA-256 is
`fd978f0573c7745de279f07c271ea713760592ecf469b50cac16916cb3e022bf`;
CSS SHA-256 remains
`5ce03a2b9ab8936b7ed5bf225002bfc74aef3c9f491f7816a052a4148a9f3312`.
Build JavaScript changed as expected from component logic; `frontend/vite.config.ts`
and `frontend/src/lib/config.ts` hashes remain the 035.3G baseline, so the
source-map and loopback-origin release risks are **not** closed. Build output
and browser traces are local/Git-ignored, not versioned/off-host proof.

## Protection and acceptance boundary

Package-lock hash stayed
`1fdf9b6d438cedc1f4027a43195407bcc1f2363f4acac50862f3403c6aa195d5`.
Protected `app/services/grounded_answer_service.py` hash stayed
`4c9d4c648bbcef30a35c4e2ca01fad0093ed0e7a8aebb777dc78b478b345c919`;
the frozen 035.3B `permission-safety.json` hash stayed
`b6e0f415dee409be55786fb4788cf9888d06890e0cfe684444013a5a1196714f`.
Active V2 API/worker/PostgreSQL/Redis container identities remained
`9d510d8b8027` / `2afc4af27fe5` / `1a5a658a2ef2` / `db2961fc9413`,
healthy with restart counts zero. The API and worker image IDs are still
different. No active V2 data or failed candidate was exercised or changed.

For TASK-035 P14, the **specific confirmation-dialog keyboard sub-check is
remediated in local/mock scope**; P14 is not fully PASS because broader
accessibility, primary workflow and live backend evidence remain gaps. For
R19, the previous accessibility failure is closed in this scope, but current
same-source live frontend/backend E2E and production delivery remain
**EVIDENCE_GAP**. Manual screen-reader review, whole-app focus/contrast,
mobile workflow audit and background inertness/assistive-technology behavior
were not certified. B19/B21/R18 RAG answer-safety failures, active API/worker
skew, production origin/source-map policy, source hygiene and owner decisions
are unchanged. Approved deferrals: zero. RC: NO-GO.
