/** Standalone Tailwind CLI config (no npm). Scans compiled templates. */
module.exports = {
  content: ["./templates/**/*.html"],
  theme: {
    extend: {
      colors: {
        primary: "#9E2820",
      },
      fontFamily: {
        display: ['"Work Sans"', '"Arial Black"', "sans-serif"],
        body: ['"Open Sans"', "Arial", "Helvetica", "sans-serif"],
      },
    },
  },
  plugins: [],
};
