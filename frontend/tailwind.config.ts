import type { Config } from "tailwindcss";

export default {
  darkMode: ["class", '[data-theme="dark"]'],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Geist", "Segoe UI", "Arial", "sans-serif"],
        mono: ["Geist Mono", "Cascadia Mono", "Consolas", "monospace"],
      },
      colors: {
        canvas: "rgb(var(--color-canvas) / <alpha-value>)",
        surface: "rgb(var(--color-surface) / <alpha-value>)",
        elevated: "rgb(var(--color-elevated) / <alpha-value>)",
        border: "rgb(var(--color-border) / <alpha-value>)",
        ink: "rgb(var(--color-ink) / <alpha-value>)",
        muted: "rgb(var(--color-muted) / <alpha-value>)",
        accent: "rgb(var(--color-accent) / <alpha-value>)",
        "accent-contrast": "rgb(var(--color-accent-contrast) / <alpha-value>)",
        success: "rgb(var(--color-success) / <alpha-value>)",
        warning: "rgb(var(--color-warning) / <alpha-value>)",
        danger: "rgb(var(--color-danger) / <alpha-value>)",
      },
      boxShadow: {
        panel: "var(--shadow-panel)",
        focus: "0 0 0 3px rgb(var(--color-accent) / 0.22)",
      },
      borderRadius: {
        token: "var(--radius-md)",
      },
      // D-2: the bare `transition` class may animate colour (hover/focus), opacity and transform only.
      transitionProperty: {
        DEFAULT: "color, background-color, border-color, text-decoration-color, opacity, transform",
      },
      transitionDuration: {
        DEFAULT: "150ms",
        fast: "150ms",
        base: "220ms",
        slow: "320ms",
      },
      transitionTimingFunction: {
        DEFAULT: "cubic-bezier(0.2, 0, 0, 1)",
        product: "cubic-bezier(0.2, 0, 0, 1)",
      },
    },
  },
  plugins: [],
} satisfies Config;
