# TASK-035.3G — bounded keyboard/accessibility verification

Date: 2026-10-14. Local Vite + mocked Chromium only; no active V2 call,
screen-reader session, axe tool, WCAG certification, or production browser
review. Contract: TASK-028 calls for accessible controls, responsive layout,
clear navigation and form validation; it does not specify a WCAG conformance
level. `frontend/src/test/e2e/accessibility.qualification.spec.ts` is a new
test-only file; no application behavior changed.

Command: `npm run test:e2e` with installed Playwright Chromium, 13 tests
total: **11 PASS, 2 FAIL**. The nine pre-existing mocked tests all passed.
The new four tests produced two passes and two failures. The Vite webServer
was local on `127.0.0.1:5174`; API routes in the dialog tests were mocked.
Failure traces are in ignored local `frontend/test-results/` and are not
versioned/off-host evidence.

| Check | Result | Bounded observation |
| --- | --- | --- |
| Login keyboard order and labels | PASS | Tab reached Email, Password, Sign in in that order; both fields had accessible labels. |
| Visible focus | PASS in login scope | Focused Email computed outline style was not `none` and width was positive; global `:focus-visible` is defined in `frontend/src/styles/index.css`. Other controls not audited. |
| Form validation announcement | PASS in login scope | Enter on empty login surfaced two `role="alert"` validation messages. No screen-reader announcement was observed. |
| Admin/Staff role-aware navigation | PASS in mocked scope | Existing tests showed Admin-only links present for Admin and absent for Staff; backend RBAC not exercised. |
| Mobile menu Escape | PASS in mocked scope | Existing test closes the mobile navigation on Escape and can still use chat composer. |
| Confirmation dialog initial focus | **FAIL** | After opening User Deactivate, `document.activeElement` was not inside the visible `role="dialog"`; the exact external focused element was not recorded. `ConfirmDialog.tsx` has no focus transfer. |
| Confirmation dialog Escape | **FAIL** | Pressing Escape left the Deactivate dialog visible (5-second assertion timeout). `ConfirmDialog.tsx` has no Escape handler. No deactivate action was invoked by the test. |
| Dialog focus trap / restoration | EVIDENCE_GAP | Not dynamically checked; the above failures already prevent a clean dialog keyboard gate. |
| Accessible names beyond login/dialog | EVIDENCE_GAP | Existing role/name assertions cover selected navigation and chat controls, not the full interface. |
| Mobile layout | PASS in login scope | 390×844 login had no horizontal document overflow; existing mobile menu test passed. Other workflows/screens not audited. |
| Reduced motion | PASS in login scope | With `prefers-reduced-motion: reduce`, signal animation computed `none`; CSS also disables named citation motion. Not all dynamic effects were inspected. |
| Basic text contrast | PASS for checked tokens only | sRGB calculations: ink/surface 17.51:1, muted/surface 5.68:1, accent/white 5.47:1, sidebar white/78 10.90:1, sidebar white/64 7.71:1. This is not a whole-UI DOM/color-state audit. |

The dialog has `aria-modal="true"` and a labeled heading, so the two
failures concern keyboard operation/focus, not absence of a dialog role/name.
No production source fix is authorized in this phase. The corresponding
frontend accessibility acceptance sub-check is **FAIL**; live and manual
accessibility qualification remain evidence gaps. Retain these red
qualification tests until separately authorized remediation and rerun.
