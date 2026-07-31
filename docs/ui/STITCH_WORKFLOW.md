# Stitch Workflow

TASK-028 uses Google Stitch as a design exploration source, not as the frontend architecture source of truth. No Stitch export or screen reference was present in the repository when TASK-028 started, so the implementation was built from the project requirements and the prompts in this directory.

## Operating Model

1. Generate each screen in Stitch from `STITCH_SCREEN_PROMPTS.md`.
2. Review generated layout for enterprise usability, responsive behavior, accessible contrast, and data density.
3. Keep useful layout hierarchy, spacing, and visual direction.
4. Replace all mock content with backend API data or an explicit unavailable state.
5. Split large generated screens into route, feature, shared UI, data display, and motion components.
6. Normalize design tokens in CSS variables and Tailwind theme extension.
7. Verify forms, tables, dialogs, navigation, and streaming states with automated tests.
8. Treat backend contracts as authoritative. Stitch output must not introduce new API fields or fake workflows.

## Current Export Status

- Export supplied: No.
- Source used: TASK-028 requirements, backend API specification, React/Vite production implementation.
- Comparison status: Pending external Stitch export. The report template in this file should be used when an export becomes available.

## Stitch Comparison Report Template

Screen:
- Stitch intent:
- Implemented:
- Changed:
- Reason:
- API integration:
- Accessibility adjustment:
- Responsive adjustment:
- React Bits effect:
- Performance adjustment:

## Guardrails

- Do not keep lorem ipsum or fake metrics.
- Do not keep absolute positioning that breaks responsive layouts.
- Do not keep animation in tables, forms, permission selectors, audit rows, destructive confirmations, or citation text.
- Do not add analytics dashboards beyond TASK-028 operational status.
- Do not expose provider credentials, backend secrets, internal Docker hostnames, or tokens in URLs.