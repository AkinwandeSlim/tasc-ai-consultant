import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/features/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1440px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        surface: {
          base: "hsl(var(--surface-base))",
          raised: "hsl(var(--surface-raised))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        // Semantic status colours for lead bands
        status: {
          exploring: "hsl(var(--status-exploring))",
          cold: "hsl(var(--status-cold))",
          warm: "hsl(var(--status-warm))",
          qualified: "hsl(var(--status-qualified))",
          hot: "hsl(var(--status-hot))",
        },
      },
      borderRadius: {
        lg: "12px",
        md: "8px",
        sm: "6px",
        full: "20px",
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
      },
      fontSize: {
        "body-sm": ["13px", { lineHeight: "1.5" }],
        body: ["15px", { lineHeight: "1.6" }],
        "heading-xs": ["12px", { lineHeight: "1.4" }],
        "heading-sm": ["14px", { lineHeight: "1.4" }],
        "heading-md": ["18px", { lineHeight: "1.3" }],
        "heading-lg": ["24px", { lineHeight: "1.2" }],
      },
      spacing: {
        "0.5": "2px",
        "1.5": "6px",
        "3.5": "14px",
        "4.5": "18px",
        "5.5": "22px",
        "6.5": "26px",
        "7.5": "30px",
      },
      keyframes: {
        "score-delta": {
          "0%": { opacity: "1" },
          "100%": { opacity: "0" },
        },
        "slide-in-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "score-delta": "score-delta 3s ease-out forwards",
        "slide-in-up": "slide-in-up 300ms ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
