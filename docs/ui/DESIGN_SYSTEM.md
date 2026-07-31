# Design System

## Direction

The TASK-028 interface is a premium enterprise AI workspace: restrained, high-clarity, operational, dark-shell-ready, and table-friendly for administrative screens. It is not a landing page, gaming dashboard, crypto dashboard, or analytics product.

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
- Reduced motion: CSS disables animations/transitions for `prefers-reduced-motion: reduce`.

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