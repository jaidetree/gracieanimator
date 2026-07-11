"""Seam 2 (Spec #34): model validation of ``Logo.accent_color``.

The admin keeps malformed hex from ever reaching the HTTP seam, so the accepted/
rejected cases are proven at the model via ``full_clean()``. Selection/session/
render behavior belongs to Seam 1 (a later slice) and is not duplicated here.
"""

import pytest
from django.core.exceptions import ValidationError

from branding.tests.factories import LogoFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("value", ["#aabbcc", "#abc", "#ABC", "#AABBCC"])
def test_accent_color_accepts_valid_hex(value):
    logo = LogoFactory.build(accent_color=value)
    logo.full_clean()  # raises on the invalid case; silence == accepted


@pytest.mark.parametrize(
    "value",
    [
        "#12345",  # wrong length (5 digits)
        "#aabbccdd",  # 8 digits — alpha not allowed
        "red",  # named color
        "aabbcc",  # missing leading '#'
        "#gggggg",  # non-hex digits
        "",  # empty
    ],
)
def test_accent_color_rejects_malformed_hex(value):
    logo = LogoFactory.build(accent_color=value)
    with pytest.raises(ValidationError) as exc:
        logo.full_clean()
    assert "accent_color" in exc.value.message_dict


def test_str_is_name():
    logo = LogoFactory.build(name="Primary mark")
    assert str(logo) == "Primary mark"
