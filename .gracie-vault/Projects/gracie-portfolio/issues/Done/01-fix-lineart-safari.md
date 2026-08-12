---
tags:
  - needs-triage
modified: 2026-08-09T22:43:19-04:00
---
# Fix lineart on mobile

> Migrated from GitHub issue #38.

## Description

Looks off on Safari in iOS.

## User Stories

- Users should be able to see the lineart on Mobile Safari

## Implementation Plan Overview

- Update input.css with more accurate border-image properties

## Acceptance Criteria

- [x] Users can see the lineart at the correct size on Mobile Safari

## Resolution

Same root cause as gracie-portfolio issue #39 (grid overlay): `.page::before`/
`.page::after` masked the lineart border-image with
`mask: url(clouds-mask.jpg) luminance ...`. `mask-mode: luminance` computed
from a JPEG (no native alpha channel) never renders in Safari, which flattened
the mask and threw off the lineart's rendered size/appearance on Mobile
Safari.

Fix (1 of 2): switched to the existing alpha-channel `clouds-mask.png`
(already converted in issue #39) and dropped the `luminance` keyword, matching
`#grid-overlay`'s mask in `assets/css/input.css`. No `mix-blend-mode` on this
element, so WebKit bug 250828 (tiled-layer blend loss, fixed via
`transform-gpu`) doesn't apply here -- only the luminance/JPEG bug did.

A second, unrelated Safari bug remained after the mask fix: the lineart
rendered cropped to roughly the first 10px of the SVG's left edge (top border)
and distorted (bottom border). Root cause: `lineart-top.svg` and
`lineart-bottom.svg` have a `viewBox="0 0 1376 32"` but no explicit `width`/
`height` attributes. Safari falls back to a default intrinsic size (300x150)
for SVGs used as `border-image-source` when they lack explicit dimensions,
which corrupts the `border-image-slice: 32 32 0 32` math (computed against
the wrong intrinsic size). Firefox/Chrome infer intrinsic size from the
viewBox and were unaffected.

Fix (2 of 2): added `width="1376" height="32"` to both SVGs in
`static/img/` alongside their existing `viewBox`.
