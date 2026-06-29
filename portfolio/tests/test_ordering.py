"""Unit tests for the pure renumber rule — no DB, no admin_client.

The renumber rule is the bug-prone part of drag-reordering; here it is driven
directly through its own interface with plain stand-in rows.
"""

from portfolio.ordering import renumber


class Row:
    """Minimal stand-in exposing the order field the rule reads/writes."""

    def __init__(self, order):
        self.order = order


def test_renumber_closes_gaps_from_deletes():
    # Gappy positions (1, 5, 9) collapse to a contiguous 1..3.
    rows = [Row(1), Row(5), Row(9)]
    changed = renumber(rows)
    assert [r.order for r in rows] == [1, 2, 3]
    # Only the two rows that actually moved are returned.
    assert changed == [rows[1], rows[2]]


def test_renumber_already_correct_is_a_noop():
    rows = [Row(1), Row(2), Row(3)]
    changed = renumber(rows)
    assert changed == []
    assert [r.order for r in rows] == [1, 2, 3]


def test_renumber_after_a_moved_span():
    # The caller hands rows already in final order (a moved to the front);
    # the rule rewrites every position to match that order.
    moved, b, c = Row(2), Row(1), Row(3)
    rows = [moved, b, c]
    changed = renumber(rows)
    assert [r.order for r in rows] == [1, 2, 3]
    # moved: 2->1, b: 1->2 changed; c stays at 3.
    assert changed == [moved, b]


def test_renumber_honours_a_custom_field_name():
    class PosRow:
        def __init__(self, position):
            self.position = position

    rows = [PosRow(4), PosRow(8)]
    changed = renumber(rows, field="position")
    assert [r.position for r in rows] == [1, 2]
    assert changed == rows
