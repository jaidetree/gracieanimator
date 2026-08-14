---
description: A position:absolute section with no top offset renders in its natural spot but doesn't reserve that height in the document, leaving body/html shorter than the page's real visual extent -- misdiagnosed three times as an html/body sizing bug before finding it
tags: [mistake, domain]
date: 2026-08-13
---

Reported symptom: a strip of raw `bg-surface` color exposed below the page
content, worse on iOS/iPadOS Safari but (it turned out) present in every
browser. Diagnosed and "fixed" three times against the wrong target before
finding the actual cause.

**Wrong turns (all in `assets/css/input.css`, `@layer base`):**
1. `html`/`body { min-height: 100% }` -> `min-height: 100dvh`. Reasonable
   defensive change (percentage-based heights track Safari's "large"
   viewport, not the real one once the collapsible toolbar retracts), but
   not the actual cause here.
2. Added `position: relative` to `body` so `#grid-overlay` (`absolute
   inset-0`, no other positioned ancestor) had an explicit containing block.
   Also reasonable in isolation, also not the cause.
3. Moved `position: relative` to `html` instead of `body`, on the theory
   that pairing it with `min-height: 100dvh` on the same element holding a
   `transform-gpu`'d descendant was making iOS hard-cap that element's
   box -- plausible-sounding given this exact file already has documented
   size-dependent WebKit compositing bugs on `#grid-overlay` (see
   [[Safari Loses Blend Mode And Mask On Large Composited Layers]]), but
   wrong: reproduced identically in desktop Chromium via Playwright with no
   iOS involved at all, which is what proved the theory false.

**Actual cause:** `templates/home.html`, `<section id="car-hero" class="absolute
pt-24 left-0 right-0 z-10 h-[36rem]">`. No `top`/`bottom` given, so per CSS
an absolutely positioned box with no offsets renders at its "static
position" -- i.e. exactly where it would sit in normal flow -- but being
`position: absolute` still removes it from flow entirely. Its parent
(`<main class="page">`) therefore doesn't reserve the 576px (`h-[36rem]`)
the section visually occupies. That height mismatch cascades: `.page`'s
auto height comes up short, `.site-container` (flex-col) sizes to that
short total, and `body`'s auto height follows -- while the actual painted
content (and `html.scrollHeight`, which does account for out-of-flow
descendants) extends much further. The grid overlay and background,
sized off body/html, ended up shorter than the real page, exposing flat
color in the gap.

**Fix:** `#car-hero` didn't need to be absolute at all -- only its child
`img` elements do (already `position: absolute` in CSS, anchored correctly
to any positioned ancestor). Changed the section's class from `absolute ...`
to `relative ...` (dropping the now-unneeded `left-0 right-0`, which existed
only to compensate for being pulled out of flow). Visually identical
placement (it was already rendering at its static position), but now
properly reserves its height. Confirmed via Playwright: before the fix,
`body.offsetHeight` (800) fell short of `body.scrollHeight` (1152); after,
they matched exactly, and `#grid-overlay`'s rendered height matched
`html.offsetHeight` exactly.

**Apply:**
- `position: absolute` with no `top`/`bottom`/`left`/`right` offset that
  fully constrains its box still renders in-place (via "static position")
  but always stops contributing to ancestor auto-height. If an element
  reads as "positioned to layer over other content" but has no actual
  offset overriding its natural flow position, ask whether it needs
  `position: absolute` on the *outer* wrapper at all, or only on specific
  descendants that truly need to escape flow (e.g. crossfading images).
- When a "page background/overlay doesn't reach the bottom" bug is
  reported as browser-specific (here: "only iOS/iPhone"), don't trust that
  framing too far before checking cross-browser -- test with a real
  browser (Playwright was available via `.direnv/python-3.12/bin/playwright`
  in this repo) before reaching for WebKit-specific compositing
  workarounds. The iOS-only framing here was circumstantial: the actual bug
  existed everywhere, but iOS's overscroll/toolbar behavior happened to
  make the gap more visible/reachable there first.
- Useful diagnostic signature for this exact class of bug: compare
  `element.offsetHeight` (layout box) against `element.scrollHeight`
  (content extent including out-of-flow-but-painted descendants) up the
  ancestor chain from the suspected absolutely-positioned culprit to
  `document.documentElement`. A hard mismatch at one specific ancestor
  boundary points at exactly which element's height calculation is
  excluding real content.

Related: [[Safari Loses Blend Mode And Mask On Large Composited Layers]]
