import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // ── Base ──────────────────────────────────────────────────────
        bg: {
          DEFAULT: "#07090f",
          surface: "#0e1219",
          elevated: "#131a26",
          overlay: "#0b1020",
        },
        border: {
          DEFAULT: "#1c2536",
          subtle: "#141c2b",
          focus: "#3b5280",
        },
        // ── Text ──────────────────────────────────────────────────────
        text: {
          primary: "#e2e8f5",
          secondary: "#8896b0",
          muted: "#4a5672",
          placeholder: "#3a4760",
        },
        // ── Accent (cold blue) ────────────────────────────────────────
        accent: {
          DEFAULT: "#5b8af7",
          hover: "#7099f8",
          muted: "#1d2d4d",
          bg: "#0f1f3d",
          text: "#93b5ff",
        },
        // ── Semantic ──────────────────────────────────────────────────
        success: {
          DEFAULT: "#22d3a5",
          bg: "#0a2420",
          text: "#4ee8c0",
        },
        warning: {
          DEFAULT: "#f0a832",
          bg: "#2a1f0a",
          text: "#f5c469",
        },
        error: {
          DEFAULT: "#f05252",
          bg: "#2a0f0f",
          text: "#f87171",
        },
        // ── Status ────────────────────────────────────────────────────
        status: {
          queued: "#8896b0",
          running: "#5b8af7",
          completed: "#22d3a5",
          failed: "#f05252",
        },
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "JetBrains Mono", "monospace"],
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
      },
      borderRadius: {
        "4xl": "2rem",
      },
      animation: {
        "fade-in": "fadeIn 0.2s ease-out",
        "slide-up": "slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
        "slide-in-left": "slideInLeft 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
        pulse: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        shimmer: "shimmer 1.5s infinite linear",
        blink: "blink 1s step-end infinite",
        "dot-bounce": "dotBounce 1.2s ease-in-out infinite",
        "zap-pulse": "zapPulse 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        dotBounce: {
          "0%, 80%, 100%": { transform: "translateY(0)", opacity: "0.4" },
          "40%":            { transform: "translateY(-5px)", opacity: "1" },
        },
        zapPulse: {
          "0%, 100%": { boxShadow: "0 0 8px rgba(91,138,247,0.2)" },
          "50%":       { boxShadow: "0 0 18px rgba(91,138,247,0.6)" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        slideInLeft: {
          from: { opacity: "0", transform: "translateX(-8px)" },
          to: { opacity: "1", transform: "translateX(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.5), 0 0 0 1px rgba(28,37,54,0.8)",
        "card-hover": "0 4px 16px rgba(0,0,0,0.4), 0 0 0 1px rgba(91,138,247,0.2)",
        glow: "0 0 20px rgba(91,138,247,0.15)",
        "glow-sm": "0 0 8px rgba(91,138,247,0.1)",
        modal: "0 24px 64px rgba(0,0,0,0.7), 0 0 0 1px rgba(28,37,54,1)",
      },
      backgroundImage: {
        "grid-pattern":
          "linear-gradient(rgba(91,138,247,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(91,138,247,0.03) 1px, transparent 1px)",
        "radial-glow":
          "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(91,138,247,0.15), transparent)",
        shimmer:
          "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.04) 50%, transparent 100%)",
        "accent-gradient":
          "linear-gradient(135deg, #5b8af7 0%, #7c5bf7 100%)",
      },
    },
  },
  plugins: [],
};

export default config;
