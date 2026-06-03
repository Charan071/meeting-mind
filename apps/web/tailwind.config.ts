import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50:  "#EEEEF8",
          100: "#D4D5EF",
          200: "#ABABDF",
          300: "#8182CF",
          400: "#6364BF",
          500: "#4F52B2",
          600: "#4547A0",
          700: "#393B8B",
          800: "#2D2F75",
          900: "#1E1F52",
        },
        neutral: {
          50:  "#F5F5F5",
          100: "#E8E8E8",
          200: "#D2D2D2",
          300: "#ABABAB",
          400: "#838383",
          500: "#5C5C5C",
          600: "#404040",
          700: "#333333",
          800: "#292929",
          900: "#1A1A1A",
        },
        success: "#107C10",
        warning: "#C19C00",
        error:   "#C50F1F",
      },
      fontFamily: {
        sans: ["Segoe UI", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
      borderRadius: {
        sm: "2px",
        DEFAULT: "4px",
        md: "4px",
        lg: "6px",
      },
      transitionDuration: {
        fast: "80ms",
        DEFAULT: "150ms",
        slow: "200ms",
      },
    },
  },
  plugins: [],
};

export default config;
