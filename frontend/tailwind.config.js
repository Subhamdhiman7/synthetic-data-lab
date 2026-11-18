/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b0d0c",
        panel: "#121613",
        panelSoft: "#1a211c",
        line: "#2a342d",
        cyan: "#d9ff5c",
        mint: "#9be8bd",
        amber: "#ffb66e",
        danger: "#ff877d",
        paper: "#f0eee6",
        smoke: "#a8afa5",
        signal: "#d9ff5c",
        coral: "#ff8067",
      },
      boxShadow: {
        glow: "0 0 50px rgba(217, 255, 92, 0.09)",
      },
    },
  },
  plugins: [],
};
