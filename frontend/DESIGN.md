# Frontend Design Notes

TASK-028 implements a production React/Vite frontend for the Enterprise AI Knowledge Assistant. It follows the UI documentation in `docs/ui/` and uses real backend API contracts.

- Primary shell: graphite enterprise sidebar with light workspace surfaces.
- Motion: local controlled motion primitives for login background, chat spotlight, and waiting text only.
- Data screens: table-first, accessible, compact, and minimally animated.
- Chat: explicitly communicates the TASK-027 `buffer_after_validation` SSE strategy.
- Documents/admin/audit: no mock production data and no raw secret/internal metadata display.