/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0D1614",
        surface: "#141F1C",
        raised: "#1B2925",
        line: "#2A3B36",
        teal: {
          DEFAULT: "#2F6F62",
          soft: "#3E8874",
          dim: "#1E4A40",
        },
        paper: "#F2ECDD",
        amber: {
          DEFAULT: "#E3A73C",
          soft: "#C98F2E",
          dim: "#8A611F",
        },
        ash: {
          100: "#EDEAE0",
          300: "#B9C0BB",
          500: "#7D8985",
          700: "#4B5652",
        },
        danger: "#D96C6C",
        success: "#6FBF9A",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      backgroundImage: {
        "grain": "radial-gradient(circle at 1px 1px, rgba(237,234,224,0.035) 1px, transparent 0)",
      },
      backgroundSize: {
        grain: "18px 18px",
      },
    },
  },
  plugins: [],
};
