"use strict";
// Make newly-added (unsaved) inline rows drag-sortable, not just saved ones.
//
// django-admin-sortable2 only drives rows it considers "originals"
// (`tr.has_original`): it draws the grip on `td.original > p`, its Sortable
// grabs via `handle: "td.original p"`, and its `onEnd` rewrites the order field
// of every `tr.has_original` on drop. A row added through "Add another" is
// cloned from the empty-form template, so it has neither the `has_original`
// class nor the handle `<p>` — you can't grab it and it's skipped when the
// order field is renumbered (issue #27).
//
// SortableJS evaluates `draggable`/`handle`/`onMove` at pointer time and
// re-queries `tr.has_original` at drop, so a row promoted *after* init joins in
// fully — grab, move, and order-rewrite — with no second Sortable to fight the
// one sortable2 already created on the tbody. On each `formset:added` we
// promote the new row: add `has_original` and inject an empty handle `<p>` into
// its `td.original`. The grip CSS already keys off `tr.has_original td.original
// p`, and the row's order field is rendered hidden with class `_reorder_`, so
// sortable2's `onEnd` writes to it on the next drop. If the row is never
// dragged, sortable2's `save_new` still numbers it to the end, so ordering is
// always defined.
document.addEventListener("formset:added", (event) => {
  const row = event.target;
  if (!(row instanceof HTMLElement)) return;
  if (!row.closest("fieldset.sortable")) return;
  const original = row.querySelector("td.original");
  if (!original || original.querySelector("p")) return;
  row.classList.add("has_original");
  original.insertBefore(document.createElement("p"), original.firstChild);
});
