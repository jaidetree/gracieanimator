"""Seam 3 (Spec #34, slice #37): the accent color is exposed as reusable
Tailwind utilities.

These assert the *compiled* artifact (`static/css/stylesheet.css`), not the
config: the safelist only matters once the CSS is rebuilt, and prod serves the
committed build. The utilities must be present even though no template
references them yet (applying accent is the owner's later redesign work), and
must resolve to the runtime `--color-accent` #36's header render emits.
"""

from pathlib import Path

from django.conf import settings

STYLESHEET = Path(settings.BASE_DIR) / "static" / "css" / "stylesheet.css"

ACCENT_UTILITIES = {
    ".bg-accent": "background-color:var(--color-accent)",
    ".text-accent": "color:var(--color-accent)",
    ".border-accent": "border-color:var(--color-accent)",
}


def _css() -> str:
    return STYLESHEET.read_text()


def test_accent_utilities_compiled_and_resolve_to_variable():
    css = _css()
    for selector, declaration in ACCENT_UTILITIES.items():
        assert f"{selector}{{{declaration}}}" in css


def test_primary_color_is_unchanged():
    # Accent is additive: the fixed brand `primary` (#9E2820) stays a literal
    # colour, not the runtime variable.
    assert ".bg-primary{--tw-bg-opacity:1;background-color:rgb(158 40 32" in _css()
