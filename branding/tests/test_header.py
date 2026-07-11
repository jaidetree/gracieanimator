"""Seam 1 (Spec #34, slice #36): the HTTP chain — context processor picks a
logo, writes it to the session, and ``base.html`` renders it seamlessly.

One ``client.get("/")`` exercises context processor → random pick → session
write → render. ``random.choice`` is monkeypatched to make selection
deterministic. Hex validation lives in ``test_models.py`` (Seam 2) and is not
duplicated here.
"""

import random

import pytest

from branding.context_processors import DEFAULT_ACCENT
from branding.tests.factories import LogoFactory

pytestmark = pytest.mark.django_db

HOME_URL = "/"

SR_ONLY_H1 = '<h1 class="sr-only">The Grace Space</h1>'


@pytest.fixture
def pick_first(monkeypatch):
    """Force selection to the first active candidate so a GET is deterministic."""
    monkeypatch.setattr(random, "choice", lambda seq: seq[0])


def _get(client):
    return client.get(HOME_URL).content.decode()


def test_first_get_picks_stores_and_renders(client, pick_first):
    logo = LogoFactory(accent_color="#123abc")

    body = _get(client)

    assert client.session["logo_id"] == logo.id
    assert "--color-accent:#123abc}" in body
    assert logo.image.url in body
    assert SR_ONLY_H1 in body


def test_second_get_keeps_the_same_logo(client, pick_first):
    chosen = LogoFactory(name="A", accent_color="#aaaaaa")
    _get(client)
    assert client.session["logo_id"] == chosen.id

    # A second active logo would be pickable on a re-pick; stickiness must not.
    LogoFactory(name="B", accent_color="#bbbbbb")
    body = _get(client)

    assert client.session["logo_id"] == chosen.id
    assert "--color-accent:#aaaaaa}" in body


def test_only_active_logos_are_selected(client, pick_first):
    active = LogoFactory(name="Active", accent_color="#0000ff", is_active=True)
    LogoFactory(name="Aardvark", accent_color="#ff0000", is_active=False)

    body = _get(client)

    assert client.session["logo_id"] == active.id
    assert "--color-accent:#0000ff}" in body


def test_empty_pool_renders_text_title_and_default_accent(client):
    body = _get(client)

    assert "logo_id" not in client.session
    assert f"--color-accent:{DEFAULT_ACCENT}}}" in body
    assert '<h1 class="site-title' in body  # visible text heading
    assert 'alt=""' not in body  # no decorative logo <img>


def test_inactive_session_logo_is_repicked(client, pick_first):
    stale = LogoFactory(name="Only", accent_color="#abcdef")
    _get(client)
    assert client.session["logo_id"] == stale.id

    stale.is_active = False
    stale.save()
    replacement = LogoFactory(name="Zzz", accent_color="#fedcba")

    body = _get(client)

    assert client.session["logo_id"] == replacement.id
    assert "--color-accent:#fedcba}" in body


def test_deleted_session_logo_is_repicked(client, pick_first):
    doomed = LogoFactory(name="Doomed", accent_color="#111111")
    _get(client)
    assert client.session["logo_id"] == doomed.id

    replacement = LogoFactory(name="Zed", accent_color="#222222")
    doomed.delete()

    body = _get(client)

    assert client.session["logo_id"] == replacement.id
    assert "--color-accent:#222222}" in body
