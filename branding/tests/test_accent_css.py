"""Seam 3 (Spec #34, slice #37): the accent color is exposed as reusable
Tailwind utilities.

These assert the *compiled* artifact (`static/css/stylesheet.css`), not the
config: the safelist only matters once the CSS is rebuilt, and prod serves the
committed build. The utilities must be present even though no template
references them yet (applying accent is the owner's later redesign work), and
must resolve to the runtime `--color-accent` #36's header render emits.

Each utility wraps the variable in `color-mix(... , transparent)` so the opacity
modifier (`bg-accent/50`) works while `--color-accent` stays a plain hex the
header can emit verbatim. Following 5066b9b, these match the *shape* of that
value rather than its minified byte layout: the load-bearing parts are the
property, the variable, and the mix against `transparent` that carries the
alpha. The exact alpha expression is Tailwind's internal spelling of
`<alpha-value>` and is deliberately not pinned.
"""

import re
from pathlib import Path

from django.conf import settings

STYLESHEET = Path(settings.BASE_DIR) / "static" / "css" / "stylesheet.css"

# Utility -> the property it must set to the accent colour.
ACCENT_UTILITIES = {
    ".bg-accent": "background-color",
    ".text-accent": "color",
    ".border-accent": "border-color",
}


def _css() -> str:
    return STYLESHEET.read_text()


def _declaration_block(css, selector):
    """The body of the rule for exactly `selector`, or None if it isn't compiled.

    Anchoring on `{` keeps `.bg-accent` from matching a variant that merely
    starts with it, e.g. `.bg-accent\\/50{...}`.
    """
    match = re.search(rf"{re.escape(selector)}\s*{{([^}}]*)}}", css)
    return match.group(1) if match else None


def _mixes_accent_with_transparent(block, prop):
    """Whether `block` sets `prop` to the accent variable mixed against
    `transparent` — the form that makes the opacity modifier resolve.

    `prop` is matched at a declaration boundary so `color` does not match inside
    `background-color`.
    """
    pattern = (
        rf"(?:^|;)\s*{re.escape(prop)}\s*:\s*"
        r"color-mix\(\s*in\s+srgb\s*,\s*var\(\s*--color-accent\s*\)"
        r"[^;]*?,\s*transparent\s*\)"
    )
    return re.search(pattern, block) is not None


def test_accent_utilities_compiled_and_resolve_to_variable():
    css = _css()
    for selector, prop in ACCENT_UTILITIES.items():
        block = _declaration_block(css, selector)
        assert block is not None, f"{selector} is missing from the compiled CSS"
        assert _mixes_accent_with_transparent(block, prop), (
            f"{selector} must set {prop} from var(--color-accent), got: {block}"
        )


def test_primary_color_is_unchanged():
    # Accent is additive: the fixed brand `primary` (#9E2820) stays a literal
    # colour, not the runtime variable.
    assert ".bg-primary{--tw-bg-opacity:1;background-color:rgb(158 40 32" in _css()
