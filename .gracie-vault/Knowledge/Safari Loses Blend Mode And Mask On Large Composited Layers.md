---
description: Safari loses mix-blend-mode on large composited layers (WebKit bug 250828, fix -- transform-gpu); loses mask-mode luminance from JPEG regardless (fix -- alpha-channel PNG)
tags: [domain]
date: 2026-08-12
---

Fixing gracie-portfolio issue #39 (grid overlay pattern in
`assets/css/input.css`, `#grid-overlay`) surfaced two distinct, real WebKit
bugs that were initially misdiagnosed as one categorical "mix-blend-mode +
mask don't combine in Safari" limitation (see the now-corrected
[[Safari Drops Mix Blend Mode Combined With Mask]]). Both bugs are
size/asset-dependent, which is why the symptom looked identical across many
unrelated DOM/positioning rewrites -- none of those rewrites touched the
actual causes.

**Bug 1 -- blend mode on large layers:**
[WebKit bug 250828](https://bugs.webkit.org/show_bug.cgi?id=250828). A
composited layer loses `mix-blend-mode` when it crosses WebKit's internal
tiled/non-tiled rendering threshold, which happens for large layers (the
reporter's viewport was ~3081x1105px on a 40" display -- comfortably past
whatever threshold). A partial fix landed upstream (Sept 2024) but only
re-applies the blend mode on a tiling-mode *transition*; an element that's
already large on its first paint can still start out broken.

**Fix:** force the element onto its own dedicated compositing layer from the
start with `transform: translateZ(0)` / `translate3d(...)` -- in this
Tailwind codebase, the `transform-gpu` utility. This sidesteps the buggy
tiled-layer path entirely.

**Bug 2 -- mask-mode: luminance from a JPEG:** independent of bug 1. A
`mask: url(foo.jpg) luminance ...` (computing luminance from an image with no
native alpha channel) did not render in Safari at all, even after fixing bug
1. Switching to a PNG with a real alpha channel and standard alpha masking
(no `luminance` keyword) fixed it immediately. Converted via Pillow:
grayscale the source, then use it as the alpha channel of a new RGBA PNG.

**Apply:**
- Reaching for `mix-blend-mode` on a large (viewport-or-bigger) element in a
  WebKit target? Add `transform-gpu`/`translateZ(0)` defensively up front.
- Reaching for a luminance `mask` sourced from a JPEG/other alpha-less format
  in a WebKit target? Convert to a PNG with a real alpha channel and drop the
  `luminance` keyword instead of debugging the luminance path.
- Removing a negative `z-index` while chasing a stacking bug carries risk:
  the element then paints *above* static siblings per normal CSS stacking
  order (positioned + `z-index: auto` outranks non-positioned content), which
  can silently make a decorative overlay intercept clicks across the whole
  page. Pair any such change with `pointer-events-none` on the overlay and
  `relative z-<n>` on the content it should sit under.

Related: [[Safari Drops Mix Blend Mode Combined With Mask]]
