---
tags:
  - needs-triage
modified: 2026-08-10T02:44:42-04:00
---
# Fix grid styles on Safari

> Migrated from GitHub issue #39.

## Description

Lower the grid opacity or diagnose why mix-blend-mode is not seemingly working on Safari.

### Expected

What it should look like:  
![](</Attachments/CleanShot 2026-08-10 at 02.18.09@2x.png>)

### Actual

It looks like:  
![](</Attachments/CleanShot 2026-08-10 at 02.12.35@2x.png>)

## Resolution

Root cause found: two distinct, stackable WebKit bugs, both size-dependent
(the reporter tests on a ~40" display, so the overlay is a genuinely large
composited layer -- ~3081x1105px):

1. **Blend mode**: [WebKit bug 250828](https://bugs.webkit.org/show_bug.cgi?id=250828)
   -- large composited layers lose `mix-blend-mode` when they cross WebKit's
   internal tiled/non-tiled rendering threshold. Fixed by adding
   `transform-gpu` (`translate3d(...)`) to `#grid-overlay`, forcing it onto
   its own dedicated compositing layer up front so it never takes the buggy
   path.
2. **Mask**: `mask-mode: luminance` computed from a JPEG (no native alpha
   channel) didn't render in Safari even with the layer fix above. Converted
   `clouds-mask.jpg` to `clouds-mask.png` with a real alpha channel (via
   Pillow: grayscale source promoted to the alpha channel) and switched to
   standard alpha masking. Confirmed working.

Ruled out along the way, for reference: the `:has(#mask-checkbox:checked)`
selector toggling the mask on/off was not the trigger (mask still failed even
applied unconditionally); horizontal page overflow was not the cause (the
large computed size was a legitimate viewport). Four earlier structural
variants (pseudo-element vs real element, fixed vs absolute, isolated vs not)
all failed identically before the actual root causes were identified -- worth
remembering that a bug reproducing identically across unrelated CSS
restructuring is a sign to look for something size/asset-related, not to keep
trying more positioning permutations.

Also hardened: `#grid-overlay` no longer has a negative `z-index` (that broke
the `transform-gpu` compositing fix), so it now paints above static content by
default. Added `pointer-events-none` to the overlay and `relative z-10` to
`.site-container` to keep the page fully interactive and correctly layered.
