import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Ningún estado depende solo del color (CONVENTIONS 14): cada uno lleva
        // además texto e icono.
        ink: "#12181f",
        muted: "#5b6672",
        line: "#d7dee5",
        surface: "#ffffff",
        canvas: "#f4f6f8",
        accent: "#1f5f8b",
        caution: "#8a5a00",
        alert: "#8b1f2b",
      },
      minHeight: { touch: "44px" },
      minWidth: { touch: "44px" },
    },
  },
  plugins: [],
};

export default config;
