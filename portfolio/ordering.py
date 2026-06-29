"""Pure ordering rules, free of DB and admin wiring.

The renumber rule is the bug-prone part of drag-reordering (gaps left by
deletes, the add-at-end default, a moved span). Keeping it here — taking the
already-ordered rows and returning only the ones that changed — gives it its
own test surface: the interface *is* the test surface.
"""


def renumber(rows, field="order"):
    """Renumber an ordered sequence 1..N; return only the rows that changed.

    ``rows`` is any sequence already in the desired final order. Each row that
    isn't yet sitting at its 1-based position has ``field`` set to that position
    and is collected; rows already correct are skipped. The changed rows are
    mutated in place and returned, ready for a ``bulk_update``.
    """
    changed = []
    for position, obj in enumerate(rows, start=1):
        if getattr(obj, field) != position:
            setattr(obj, field, position)
            changed.append(obj)
    return changed
