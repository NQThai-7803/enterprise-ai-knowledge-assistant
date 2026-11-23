# Frontend Design Notes

The 2026-11 redesign follows `docs/ui/redesign-plan.md` (owner-approved) and the design canvas "EAKA – UI Animation". Tokens, motion rules and accessibility rules are in `docs/ui/DESIGN_SYSTEM.md`; backend contracts the UI relies on are tracked in `docs/ui/backend-requests.md`.

- Shell: light grouped sidebar, no top bar, API readiness as a status dot (D-6), mobile drawer.
- Chat: conversation list | conversation | citations. Answers appear whole after validation (`buffer_after_validation`). ANSWERED shows "Đã xác minh nguồn"; NO_ANSWER a neutral dashed card; unverified sentences come from the server's `segments` (BR-3), never from matching words in the UI.
- Documents: BR-1 version fields, scope and status badges; the viewer `/documents/:id/view?page=N` opens `/preview` in a new tab (D-7, BR-2).
- Names of other people or departments only when the response carries them (BR-4 option a, Admin).
- Admin screens: tables, a native `<dialog>` drawer for user forms, no decorative motion on Permissions and Audit.
