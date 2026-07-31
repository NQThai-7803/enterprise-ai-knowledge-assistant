# Stitch Screen Prompts

Use these prompts one screen at a time. The product is an Enterprise AI Knowledge Assistant for authenticated enterprise users who manage documents, grounded chat, citations, feedback, audit logs, and system status. Use a desktop-first layout, responsive adaptation, accessible contrast, clear focus states, and restrained premium enterprise styling. Reserve motion areas for later controlled React Bits-inspired implementation; do not animate tables, forms, destructive actions, permission selectors, audit rows, or citation text.

## 1. Login

Design a login screen for an enterprise AI knowledge assistant. The objective is secure authentication, not a marketing landing page. Use a restrained premium technology aesthetic with a subtle dark graphite/navy application background and a clean white or dark-ready sign-in surface. Include email, password, submit button, safe validation error area, expired-session warning area, and an enterprise product name. Desktop-first: content and sign-in panel can sit in a balanced two-column layout; mobile stacks form first after product signal. Use one decorative animated background region behind the product area only. Prohibit animation in the password input and error messages.

## 2. Main Application Shell

Design the authenticated application shell. Objective: fast navigation across Chat, Documents, Users, Departments, Feedback, Audit logs, System status, and Profile. Include collapsible sidebar, role-aware navigation, current user section, header with contextual title, API readiness indicator, breadcrumb/title area, responsive mobile drawer, and clear main content region. Use dense but readable spacing and strong active-route affordance. Reserve a very subtle sidebar active-item hover effect. No animated background in the shell.

## 3. AI Chat Workspace

Design a workspace for grounded AI chat. Include session sidebar, active conversation, message composer, validated citation panel, provider/model status, stream waiting state, stop action, retry/error state, and empty state. Make it spacious but operational. Show that validated answer content appears after source checking; do not imply chain-of-thought. Reserve a soft spotlight around the active assistant response and a subtle waiting animation. Prohibit animation in citations and message text after completion.

## 4. Document Library

Design a paginated document library. Include search, status filter, access-scope filter, uploader/department columns when available, processing status, file size/type, updated date, and permission-aware actions. Use table-first desktop layout and responsive horizontal scroll or compact cards on mobile. Empty, loading, and error states must be explicit. No decorative animation in the table.

## 5. Document Upload

Design a document upload screen for PDF ingestion. Include drag-and-drop zone, file picker, title, description, access scope, department selector, validation errors, upload action, upload progress state, backend processing state, success and failure notices, and retry. Distinguish upload completion from processing readiness. Reserve a small processing shimmer only in the status area. Prohibit fake completion percentages.

## 6. Document Detail and Processing Status

Design a document detail screen. Include metadata, status, processing state, safe error details, uploader, owner/department, file size, created/updated time, download action, permission action if authorized, and destructive delete confirmation entry point. Use a two-column desktop layout with status summary on the side. No raw storage path or internal queue details.

## 7. Document Permission Management

Design a permissions management screen. Include existing grants, user/department grant controls, permission level selector, duplicate prevention messaging, revoke action with confirmation, and safe empty/error states. Layout should be compact and auditable. Prohibit decorative motion and color-only status.

## 8. User Management

Design admin user management. Include paginated/searchable user list if available, role, department, active state, create user dialog, edit allowed fields, activate/deactivate actions, validation, and confirmation for destructive changes. Prioritize table clarity over visuals. No fake password reset workflow unless API supports it.

## 9. Department Management

Design department management. Include list, create/edit form, code, name, description, active state if available, conflict handling, and empty/error states. Keep it operational and compact. No member count unless the API returns it.

## 10. Feedback Management

Design feedback management for admins/managers. Include feedback list, rating, optional reason/comment, created date, message id/reference, filters if supported, and safe detail drawer. Also define a compact answer feedback control for chat messages. Avoid exposing full private answer content unless backend returns it.

## 11. Audit Log Explorer

Design a dense audit log explorer. Include pagination, timestamp, actor, action/event type, target/resource, outcome, request id, error code, safe metadata, filters, and detail drawer. This screen must be clear, scannable, and minimally animated. Do not show prompts, document content, answers, tokens, API keys, raw exceptions, or authorization headers.

## 12. System and LLM Provider Status

Design a system status screen for operational testing. Include API live/ready, PostgreSQL, Redis, worker when available, LLM enabled/disabled, selected provider display name, selected model display name, configuration status, SSE capability, and grounding strategy. Show unavailable states when backend endpoints do not exist. Reserve one subtle status hero surface. Do not allow arbitrary provider URL entry or automatic external provider calls.

## 13. Profile and Account

Design profile/account screen. Include current user identity, role, department, active status, session information, logout action, and security guidance as short operational labels. Do not expose tokens or raw claims. Mobile layout should be single-column.

## 14. Access Denied

Design a safe access-denied page. Include concise title, role-safe message, action back to allowed workspace, and request reference area if available. No sensitive resource names. No dramatic animation.

## 15. Not Found

Design a not-found page. Include product shell-compatible layout, concise message, link back to Chat or Documents, and no raw path details beyond the browser URL. No marketing hero.

## 16. General Error

Design a general error state. Include safe message, reload/retry action, optional request id, and clear visual hierarchy. Do not show stack trace or raw API body. Must fit inside route-level panels and full-page fallback.

## 17. Empty States

Design reusable empty states for chat, documents, feedback, audit logs, and permissions. Include specific titles, concise descriptions, and permission-aware actions. Use one premium but quiet illustration/motion area only where it improves clarity. No fake data previews.

## 18. Loading and Skeleton States

Design reusable page, table, card, inline, chat waiting, document processing, and citation loading states. Loading states should preserve layout dimensions and avoid layout shift. Use reduced-motion-friendly shimmer or subtle text entrance. Do not animate table rows continuously after content appears.