import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        term: {
          bg: "#070A0F",
          panel: "#0D121A",
          border: "#1C2633",
          amber: "#FFB000",
          green: "#22C55E",
          red: "#EF4444",
          cyan: "#22D3EE",
          dim: "#6B7A8C",
          text: "#D7DEE7",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "IBM Plex Mono", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
