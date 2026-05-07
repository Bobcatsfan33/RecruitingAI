import type { Config } from "tailwindcss";

// "Salesforce meets macOS" — see docs/UI-DESIGN-DIRECTION.md.
//
// Colour tokens live as CSS custom properties on :root in styles/tokens.css
// so dark/light mode is a single class flip. Tailwind exposes those via
// arbitrary values (`text-[var(--text-primary)]`) but we also map the
// common ones into Tailwind's theme so most components don't need
// arbitrary syntax.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        canvas: "var(--bg-canvas)",
        surface: "var(--bg-surface)",
        elevated: "var(--bg-elevated)",
        vibrancy: "var(--bg-vibrancy)",
        border: "var(--border-subtle)",
        primary: "var(--text-primary)",
        secondary: "var(--text-secondary)",
        accent: "var(--accent)",
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
        sf: "var(--brand-salesforce)",
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"SF Pro Text"',
          '"SF Pro Display"',
          '"Inter"',
          'system-ui',
          'sans-serif',
        ],
        mono: [
          '"SF Mono"',
          '"JetBrains Mono"',
          'ui-monospace',
          'Menlo',
          'monospace',
        ],
      },
      borderRadius: {
        xs: "4px",
        sm: "6px",
        DEFAULT: "8px",
        md: "10px",
        lg: "14px",
        xl: "18px",
        "2xl": "24px",
      },
      boxShadow: {
        // Soft macOS-window shadow.
        window: "0 1px 0 rgba(0,0,0,0.04), 0 18px 48px -16px rgba(0,0,0,0.18)",
        elevated:
          "0 0 0 1px var(--border-subtle), 0 4px 12px -4px rgba(0,0,0,0.10)",
      },
      backdropBlur: {
        vibrancy: "20px",
      },
    },
  },
};

export default config;
