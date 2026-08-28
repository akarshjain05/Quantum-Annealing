/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#F8FAFC",
        surface: "#FFFFFF",
        raised: "#F1F5F9",
        border: "#E2E8F0",
        text: "#0F172A",
        muted: "#64748B",
        faint: "#CBD5E1",
        gold: { 
          DEFAULT: "#059669", 
          dim: "#D1FAE5" 
        },
        teal: { 
          DEFAULT: "#1E3A8A", 
          500: "#1E3A8A", 
          600: "#1E40AF", 
          400: "#2563EB", 
          dim: "#DBEAFE" 
        },
        red: { 
          DEFAULT: "#DC2626", 
          500: "#DC2626",
          dim: "#FEE2E2" 
        },
        yellow: {
          500: "#D97706"
        },
        green: {
          400: "#10B981"
        },
        tagreg: "#3B82F6",
        tagpractice: "#059669",
        tagassumption: "#64748B",
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
