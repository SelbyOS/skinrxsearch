module.exports = {
  content: ["./src/index.html"],
  theme: {
    extend: {
      colors: {
        canvas: "var(--bg)", ink: "var(--ink)", mute: "var(--mute)", line: "var(--line)",
        glass: "var(--glass)", accent: "var(--accent)", "on-accent": "var(--on-accent)",
        chip: "var(--chip)", warn: "var(--warn)",
        watch: "var(--c-watch)", try: "var(--c-try)", skip: "var(--c-skip)", novel: "var(--c-novel)",
      },
      fontFamily: {
        display: ["Instrument Serif", "Georgia", "serif"],
        sans: ["Figtree", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
};
