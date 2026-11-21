# Design System

## Direction

Since the 2026-11 redesign (`docs/ui/redesign-plan.md`, design canvas "EAKA – UI Animation"), the interface is light: a 240 px white sidebar grouped Làm việc / Quản trị / Tài khoản, no top bar, Geist type, accent `#0F766E`, canvas `#F4F7F9`. All visible labels are Vietnamese (`frontend/src/lib/labels.ts`); enum values stay internal. It is not a landing page or an analytics product.

## Tokens

Tokens are centralized in `frontend/src/styles/index.css` and extended through `frontend/tailwind.config.ts`.

- Colors: canvas, surface, elevated, ink, muted, border, accent, accent contrast, success, warning, danger.
- Typography: system UI stack, normal letter spacing, compact headings inside panels, larger type only on login and major empty states.
- Spacing: consistent 4px-based rhythm through Tailwind utilities.
- Radius: `--radius-token: 0.5rem`; cards and panels stay restrained.
- Shadows: small panel shadow and focus shadow.
- Focus: visible accent focus shadow and border shift.
- Status: success/warning/danger use both color and text/icon labels.
- Responsive: desktop-first shell, mobile drawer, horizontal table scroll where data comparison matters.
- Motion: CSS only, `transform` and `opacity` only, `--motion-fast` 150 ms (hover, focus, citation chip), `--motion-base` 220 ms (badge, menu, toast), `--motion-slow` 320 ms (answer, citation panel, drawer), one curve `--ease: cubic-bezier(0.2, 0, 0, 1)`. D-2 lets hover/focus change colour; the bare Tailwind `transition` class is limited to colour, opacity and transform. No typing effect: an answer appears whole after citation checks.
- Reduced motion: `prefers-reduced-motion: reduce` sets `animation: none` and `transition: none` everywhere.

## Surface Rules

- Page sections are unframed layouts or single panels. Nested cards are avoided.
- Tables remain stable and horizontally scroll on small screens.
- Chat uses a spacious center panel and a separate citation panel.
- Audit and permissions screens avoid decorative animation.

## Accessibility

- Labels are explicit and not replaced by placeholders.
- Focus states are visible.
- Async status uses `role=status` or polite live regions where appropriate.
- Decorative motion is `aria-hidden` and non-interactive.
- Color-only status is avoided.