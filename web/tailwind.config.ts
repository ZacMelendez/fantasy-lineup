import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#12151c",
        panel: "#1a1f29",
        edge: "#2a3140",
      },
    },
  },
  plugins: [],
};

export default config;
