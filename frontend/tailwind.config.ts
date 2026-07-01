import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#ecf8f5",
          100: "#d1ede4",
          200: "#a3dcc9",
          300: "#6cc4a8",
          400: "#38a887",
          500: "#1a8c6e",
          600: "#0d7159",
          700: "#0a5a48",
          800: "#094838",
          900: "#073a2e",
        },
        paper: {
          50: "#fdfcf9",
          100: "#faf9f5",
          200: "#f5f3ec",
          300: "#eae6da",
        },
        ink: {
          50: "#f6f5f3",
          100: "#e7e5e0",
          200: "#d1cdc4",
          300: "#a8a298",
          400: "#7a7468",
          500: "#57514a",
          600: "#3d3833",
          700: "#2a2622",
          800: "#1c1917",
          900: "#0f0e0d",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "Noto Serif SC", "serif"],
        sans: ["var(--font-sans)", "Noto Sans SC", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 3px 0 rgba(28, 25, 23, 0.04), 0 1px 2px 0 rgba(28, 25, 23, 0.02)",
        "card-hover": "0 8px 24px -4px rgba(28, 25, 23, 0.08), 0 2px 8px -2px rgba(28, 25, 23, 0.04)",
        "brand-sm": "0 1px 3px 0 rgba(13, 113, 89, 0.12)",
        brand: "0 4px 14px -2px rgba(13, 113, 89, 0.25)",
      },
      animation: {
        "fade-in": "fadeIn 0.4s ease-out",
        "slide-up": "slideUp 0.5s ease-out",
        "stagger": "slideUp 0.5s ease-out both",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
