/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0A0E13",
        surface: "#10151C",
        raised: "#171E27",
        border: "#263041",
        text: "#E7ECF3",
        muted: "#7C8AA0",
        faint: "#4A5568",
        gold: { DEFAULT: "#C7A24C", dim: "#8A7238" },
        teal: { DEFAULT: "#4FB8AE", dim: "#336B65" },
        red: { DEFAULT: "#D66B56", dim: "#7A3B2F" },
        tagreg: "#6E8FE0",
        tagpractice: "#C7A24C",
        tagassumption: "#8B8698",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'IBM Plex Sans'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      fontFeatureSettings: {
        tabular: '"tnum"',
      },
    },
  },
  plugins: [],
};
