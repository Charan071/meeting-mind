import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50:  "#F4F4FC",
          100: "#E3E3F3",
          200: "#C5C6E8",
          300: "#A7A8DC",
          400: "#8788CF",
          500: "#6264A7",
          600: "#4F5196",
          700: "#3D3E82",
          800: "#2D2E6B",
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
          850: "#201F1E",
          900: "#1A1A1A",
        },
        success: "#107C10",
        warning: "#C19C00",
        error:   "#C50F1F",
      },
      fontFamily: {
        sans: ["Segoe UI", "system-ui", "-apple-system", "sans-serif"],
        mono: ["Cascadia Code", "Consolas", "monospace"],
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
