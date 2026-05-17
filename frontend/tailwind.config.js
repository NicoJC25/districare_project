/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#F7FAFC",
        surface: "#FFFFFF",
        "surface-muted": "#F0F5F2",
        "surface-raised": "#EAEEEF",
        border: "#D9E2EC",
        outline: "#BCC9C5",
        text: "#102A43",
        muted: "#62748E",
        sidebar: "#0B1F33",
        primary: "#0E9384",
        "primary-dark": "#00685D",
        secondary: "#2563EB",
        success: "#16A34A",
        warning: "#F79009",
        danger: "#D92D20",
        purple: "#7C3AED",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 3px rgba(16, 42, 67, 0.06)",
      },
      borderRadius: {
        card: "0.5rem",
      },
    },
  },
  plugins: [],
};
