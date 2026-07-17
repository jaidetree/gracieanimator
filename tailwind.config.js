/** Standalone Tailwind CLI config (no npm). Scans compiled templates. */
module.exports = {
	content: ['./templates/**/*.html'],
	// Accent utilities must compile even before any template uses them (the
	// per-visitor colour is applied in the owner's later redesign work), so the
	// three consumables are safelisted rather than discovered via `content`.
	safelist: ['bg-accent', 'text-accent', 'border-accent'],
	theme: {
		extend: {
			colors: {
				primary: '#9E2820',
				surface: '#090808',
				// Backed by the runtime `--color-accent` the header render emits, so the
				// accent utilities resolve to the per-visitor logo's accent colour (#37).
				// `color-mix` applies the opacity modifier (`bg-accent/50`) while the
				// variable stays a plain hex the header can emit verbatim. Bare
				// `bg-accent` resolves `<alpha-value>` to `var(--tw-*-opacity, 1)`, which
				// the utility sets to 1, so it stays opaque.
				accent: 'color-mix(in srgb, var(--color-accent) calc(<alpha-value> * 100%), transparent)',
			},
			fontFamily: {
				display: ['"Exo 2"', '"Arial Black"', 'sans-serif'],
				body: ['"Work Sans"', 'Arial', 'Helvetica', 'sans-serif'],
			},
		},
	},
	plugins: [],
}
