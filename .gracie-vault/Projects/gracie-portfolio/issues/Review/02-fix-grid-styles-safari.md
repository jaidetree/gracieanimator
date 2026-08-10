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

Confirmed as a genuine Safari/WebKit limitation, not a CSS mistake: `body::before`
combines `mix-blend-mode: soft-light` with a `mask` (the clouds mask, applied
conditionally). In Safari this pseudo-element renders fully opaque, with
neither the blend nor the mask applied, regardless of positioning strategy.

Ruled out via manual Safari testing across four structural variants, all with
the identical symptom (flat opaque grid, no blend, no mask):
- pseudo-element, `position: fixed` (original)
- pseudo-element, `position: absolute`
- real `<div>` element, `position: fixed`
- real `<div>` element, `position: absolute` + `isolation: isolate` + explicit
  `z-index` stacking

Since restructuring the DOM/positioning didn't change the outcome, applied the
ticket's own fallback: a Safari-only `@supports (-webkit-touch-callout: none)`
override that drops the grid's opacity to `0.05` there, so the un-blended flat
grid reads as a faint texture instead of a solid overlay. Tuned interactively
against Safari by the reporter. `body`'s `bg-fixed` was also dropped as part of
the same pass.
