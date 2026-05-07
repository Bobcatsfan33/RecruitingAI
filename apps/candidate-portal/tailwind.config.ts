import type { Config } from "tailwindcss";

// Same Salesforce-meets-macOS token contract as the command-center app.
// Candidate side leans slightly lighter / more inviting; tokens override
// in styles/tokens.css.

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
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"SF Pro Text"', '"Inter"', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        sm: "6px",
        DEFAULT: "8px",
        md: "10px",
        lg: "14px",
        xl: "18px",
        "2xl": "24px",
      },
      boxShadow: {
        window: "0 1px 0 rgba(0,0,0,0.04), 0 18px 48px -16px rgba(0,0,0,0.18)",
        elevated: "0 0 0 1px var(--border-subtle), 0 4px 12px -4px rgba(0,0,0,0.10)",
      },
      backdropBlur: { vibrancy: "20px" },
    },
  },
};
export default config;
