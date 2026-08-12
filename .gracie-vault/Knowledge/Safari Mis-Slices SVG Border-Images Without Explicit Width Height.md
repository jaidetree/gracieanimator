---
description: Safari/WebKit corrupts border-image-slice math for an SVG border-image-source that has a viewBox but no explicit width/height attributes -- falls back to a default 300x150 intrinsic size
tags: [domain]
date: 2026-08-12
---

Fixing gracie-portfolio issue #38 (lineart border on `.page::before`/
`.page::after` in `assets/css/input.css`) surfaced a second Safari bug,
independent of the luminance/JPEG mask bug fixed in the same session (see
[[Safari Loses Blend Mode And Mask On Large Composited Layers]]).

`lineart-top.svg` / `lineart-bottom.svg` (in `static/img/`) each declare
`viewBox="0 0 1376 32"` but no `width`/`height` attributes. Used as
`border-image-source` with `border-image-slice: 32 32 0 32` (values computed
for a 1376x32 image), Safari rendered the top border cropped to roughly the
first 10px of the SVG's left edge, and the bottom border visibly distorted.
Firefox and Chrome rendered both correctly.

Root cause: an SVG with only a `viewBox` (no explicit `width`/`height`) has
no CSS-visible intrinsic size in Safari, which falls back to a default
(300x150) when the image is used as a `border-image-source`. `border-image-slice`
values are interpreted against that (wrong) intrinsic size, so the slice
offsets land far outside the actual artwork -- consistent with "shows only a
sliver near one edge."

**Fix:** add explicit `width`/`height` attributes matching the `viewBox`
dimensions to any SVG used as a `border-image-source` (or any CSS image
context that needs an intrinsic size, e.g. `mask`, plain `background-image`
sizing without `background-size`). `preserveAspectRatio="none"` on these
SVGs was not the cause and did not need to change.

**Apply:** when an SVG renders wrong specifically in Safari but fine in
Firefox/Chrome, and the SVG is used somewhere CSS needs to know its
intrinsic size (`border-image`, unsized `background-image`, `mask`), check
for a missing `width`/`height` before assuming it's a positioning or slice-value
bug -- add the attributes rather than tuning slice/size values to compensate.

Related: [[Safari Loses Blend Mode And Mask On Large Composited Layers]]
