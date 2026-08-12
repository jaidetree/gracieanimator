---
description: Safari/WebKit renders an element flat and opaque -- no blend, no mask -- when mix-blend-mode and mask are applied to the same element
tags: [domain]
date: 2026-08-10
---

Safari/WebKit fails to apply `mix-blend-mode` **and** `mask` together on the
same element: the element renders fully opaque with neither effect applied.
This held across four structurally different variants tested manually in
Safari while fixing gracie-portfolio issue #39 (grid overlay pattern):

- pseudo-element, `position: fixed`
- pseudo-element, `position: absolute`
- real `<div>` element, `position: fixed`
- real `<div>` element, `position: absolute` + `isolation: isolate` + explicit
  `z-index` stacking

All four produced the identical symptom, which rules out stacking-context /
positioning as the cause -- this is a genuine WebKit limitation, not a CSS
mistake. No amount of DOM/positioning restructuring fixed it.

**Apply:** don't burn more cycles trying to restructure DOM/positioning around
this combo in Safari. Either split blend and mask onto two stacked elements
(untested, may hit the same limitation -- verify in Safari before trusting
it), or fall back to a Safari-only override via
`@supports (-webkit-touch-callout: none) { ... }` (the standard Safari-only
`@supports` detection hack) that adjusts opacity/appearance for Safari
specifically, as shipped in `assets/css/input.css`'s `body::before` grid
overlay.

Related: [[Grid Overlay Uses Mask Plus Blend On Body Before]]

## Correction (2026-08-12)

This note's conclusion was wrong: it isn't a fundamental "can't combine
mix-blend-mode + mask" limitation. Continued investigation found two
distinct, real, **size-dependent** WebKit bugs that happened to produce the
identical symptom across all four variants above (all tested on the same
large ~3081x1105px viewport), which is why restructuring DOM/positioning
never helped -- none of those variants addressed either actual cause. See
[[Safari Loses Blend Mode And Mask On Large Composited Layers]] for the real
root causes and fix (transform-gpu + alpha-channel PNG mask instead of
luminance-from-JPEG).

**Apply:** a bug that reproduces identically across several *unrelated*
structural rewrites is a signal to stop varying that axis (positioning/DOM
shape) and look at what stayed constant instead (element size, asset format,
compositing triggers) -- not a signal that the combination is categorically
unsupported.
