/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#0b0c10",
          soft: "#121318",
          card: "#16181f",
          ring: "#2e3241",
        },
      },
      borderRadius: { "3xl": "1.5rem" },
      boxShadow: { soft: "0 10px 30px rgba(0,0,0,.35)" },
    },
  },
  plugins: [],
}
