---
name: Nexus Intelligence
colors:
  surface: '#051424'
  surface-dim: '#051424'
  surface-bright: '#2c3a4c'
  surface-container-lowest: '#010f1f'
  surface-container-low: '#0d1c2d'
  surface-container: '#122131'
  surface-container-high: '#1c2b3c'
  surface-container-highest: '#273647'
  on-surface: '#d4e4fa'
  on-surface-variant: '#c7c4d7'
  inverse-surface: '#d4e4fa'
  inverse-on-surface: '#233143'
  outline: '#908fa0'
  outline-variant: '#464554'
  surface-tint: '#c0c1ff'
  primary: '#c0c1ff'
  on-primary: '#1000a9'
  primary-container: '#8083ff'
  on-primary-container: '#0d0096'
  inverse-primary: '#494bd6'
  secondary: '#5de6ff'
  on-secondary: '#00363e'
  secondary-container: '#00cbe6'
  on-secondary-container: '#00515d'
  tertiary: '#4edea3'
  on-tertiary: '#003824'
  tertiary-container: '#00885d'
  on-tertiary-container: '#000703'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e1e0ff'
  primary-fixed-dim: '#c0c1ff'
  on-primary-fixed: '#07006c'
  on-primary-fixed-variant: '#2f2ebe'
  secondary-fixed: '#a2eeff'
  secondary-fixed-dim: '#2fd9f4'
  on-secondary-fixed: '#001f25'
  on-secondary-fixed-variant: '#004e5a'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#051424'
  on-background: '#d4e4fa'
  surface-variant: '#273647'
typography:
  display-xl:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 26px
    fontWeight: '600'
    lineHeight: '1.3'
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 22px
    fontWeight: '600'
    lineHeight: '1.3'
  title-md:
    fontFamily: Geist
    fontSize: 18px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Geist
    fontSize: 15px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-md:
    fontFamily: Geist
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1.2'
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Geist
    fontSize: 11px
    fontWeight: '500'
    lineHeight: '1.2'
    letterSpacing: 0.03em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 48px
  3xl: 64px
  sidebar-width: 280px
  container-max-width: 1200px
---

## Brand & Style
The design system is engineered for high-stakes enterprise environments where clarity, speed, and precision are paramount. The brand personality is **Technical, Secure, and Authoritative**, positioning the AI not as a toy, but as a robust knowledge partner. 

The aesthetic draws from **Minimalism** and **Modern Corporate** styles, utilizing a deep-space background to reduce eye strain during prolonged sessions. Visual interest is achieved through high-fidelity "React Bits" like subtle border glows and spotlight cards that react to user focus, signaling the "live" nature of the AI. The interface feels lightweight yet structurally sound, prioritizing content density without sacrificing legibility.

## Colors
This design system utilizes a layered dark-mode palette to establish a clear information hierarchy.
- **Backgrounds:** The base layer uses a deep charcoal (#0B0E14), while the sidebar is recessed further (#07090D) to frame the primary workspace.
- **Surfaces:** Cards and floating panels use a layered slate (#151921) to lift content visually.
- **Accents:** Refined Indigo (#6366F1) serves as the primary action color, signifying intelligence and stability. Subtle Cyan (#22D3EE) is used sparingly for data visualizations and AI-specific status indicators.
- **Feedback:** Success, Warning, and Error colors are desaturated to ensure they do not clash with the dark background while remaining accessible.

## Typography
The system uses **Geist** for its technical precision and exceptional legibility in developer and AI-centric interfaces. 
- **Internationalization:** The font choice and line-heights are optimized for Vietnamese diacritics, ensuring that stacked accents do not clip or appear crowded.
- **Hierarchy:** We use a strict contrast between `Headline-LG` for workspace titles and `Body-MD` for the primary AI output. 
- **Monospaced elements:** For AI-generated code or data strings, fall back to the monospaced variant of the font family to maintain technical character.

## Layout & Spacing
The design system operates on a rigorous **8px grid**. All margins, paddings, and component heights must be multiples of 8 to ensure visual mathematical harmony.
- **Sidebar Layout:** A fixed 280px sidebar on the left for navigation and history. 
- **Content Area:** A fluid center-aligned container with a max-width of 1200px for AI chat interfaces to maintain optimal line length for readability.
- **Responsive:** On mobile, the sidebar collapses into a drawer, and horizontal padding reduces from 32px to 16px.

## Elevation & Depth
Depth is created through **Tonal Layering** rather than heavy shadows. 
- **Level 0 (Base):** Deep Charcoal background.
- **Level 1 (Sidebar/Secondary):** Darker recessed navy.
- **Level 2 (Cards/Inputs):** Slate surface with a 0.5px or 1px translucent border (`rgba(30, 41, 59, 0.5)`).
- **Interactive Depth:** On hover, cards utilize a "Spotlight" effect where a subtle radial gradient follows the cursor, illuminating the border.
- **Shadows:** Only used for floating menus and modals, using a large, soft blur (24px-32px) with 40% opacity and no offset to create a "glow" rather than a drop shadow.

## Shapes
The design system employs a consistent **8px (0.5rem)** corner radius for most UI elements, including buttons, input fields, and cards. This radius strikes a balance between professional rigor and modern softness.
- **Buttons:** 8px radius.
- **Inputs:** 8px radius.
- **Modals/Large Cards:** 12px-16px (`rounded-lg` or `rounded-xl`) to distinguish major layout shifts.
- **Indicators:** Small status dots and profile avatars remain circular (pill-shaped).

## Components
- **Buttons:** Primary buttons use the Refined Indigo background with white text. Secondary buttons use a "Ghost" style: translucent slate border with a hover state that fills the background slightly.
- **Input Fields:** Search and chat inputs are Level 2 surfaces. They feature a 1px border that transitions to the Primary Accent color when focused. 
- **Spotlight Cards:** Knowledge base cards should implement a "React Bits" spotlight effect, where the border illuminates based on mouse proximity.
- **Chips/Tags:** Used for AI metadata. Small, 11px text, 4px vertical padding, 8px horizontal padding. Neutral background with subtle text.
- **Chat Bubbles:** AI responses should be distinguished by a very subtle left-border accent of Cyan to signify the "bot" is speaking, while user prompts remain unadorned for clarity.
- **Status Indicators:** Use a "pulsing" animation for the AI's "Thinking" state, utilizing the Secondary Accent (Cyan).