// Pre-fill the order field of a newly added comic-page inline row with the next
// number, so the editor sees the value before saving. The server (ComicAdmin
// .save_formset) is the backstop for rows left at 0 (e.g. JS disabled).
//
// Django fires a native `formset:added` event on document when a row is added;
// event.target is the new row. We only touch a blank order field so a value the
// editor typed is never clobbered.
document.addEventListener("formset:added", (event) => {
  const row = event.target;
  const orderInput = row.querySelector('input[name$="-order"]');
  // Treat 0 as "unset" to match the server backstop: the order field's model
  // default is 0, so a fresh row renders value="0", not empty.
  if (!orderInput) {
    return;
  }
  const current = orderInput.value.trim();
  if (current !== "" && current !== "0") {
    return;
  }
  const group = row.closest(".inline-group");
  if (!group) {
    return;
  }
  let max = 0;
  group.querySelectorAll('input[name$="-order"]').forEach((input) => {
    const value = parseInt(input.value, 10);
    if (!Number.isNaN(value) && value > max) {
      max = value;
    }
  });
  orderInput.value = max + 1;
});
