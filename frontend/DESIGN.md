# Frontend Design Notes

TASK-028 implements a production React/Vite frontend for the Enterprise AI Knowledge Assistant. It follows the UI documentation in `docs/ui/` and uses real backend API contracts.

- Primary shell: graphite enterprise sidebar with light workspace surfaces.
- Motion: local controlled motion primitives for login background, chat spotlight, and waiting text only.
- Data screens: table-first, accessible, compact, and minimally animated.
- Chat: explicitly communicates the TASK-027 `buffer_after_validation` SSE strategy.
- Documents/admin/audit: no mock production data and no raw secret/internal metadata display.

# Enterprise AI Knowledge Assistant Design System

## Theme
- Dark enterprise AI workspace
- Premium but restrained
- High information density

## Layout
- Navigation sidebar: 76px
- Conversation panel: 250px
- Source panel: 340px
- Header height: 64px

## Radius
- Small: 6px
- Medium: 8px
- Large: 10px

## Motion
- Page transition: 240–320ms
- Drawer: spring transition
- Citation pulse: one cycle only
- Continuous background effect: maximum one per page

## React Bits
- Animated Content: AI answer
- Animated List: conversations and sources
- Spotlight Card: selected source
- Border Glow: chat composer
- Shiny Text: AI processing
- Threads or Dark Veil: subtle background