"""HTTP-seam tests for the storyboard password gate (Slice 9).

Covers the gate from both sides: an unauthenticated visitor is redirected to the
login form on every storyboard URL; a correct POST to /auth/ sets the session
flag, which one-and-for-all unlocks the whole namespace; /logout/ clears it. The
shared password is supplied per-test via ``override_settings`` so the suite never
depends on the ambient env value.
"""

import pytest

from portfolio.tests.factories import CategoryFactory, StoryboardFactory

pytestmark = pytest.mark.django_db

INDEX_URL = "/storyboards/"
AUTH_URL = "/auth/"
LOGOUT_URL = "/logout/"


@pytest.fixture(autouse=True)
def password(settings):
    """A known shared password for every test here, reverted automatically."""
    settings.STORYBOARDS_PASSWORD = "s3cret"
    return "s3cret"


def _unlock(client):
    session = client.session
    session["storyboards_auth"] = True
    session.save()


# --- locked: every storyboard URL redirects to the login form ---


def test_index_redirects_to_login_when_locked(client):
    resp = client.get(INDEX_URL)
    assert resp.status_code == 302
    assert resp.url == f"{AUTH_URL}?next={INDEX_URL}"


def test_category_redirects_to_login_when_locked(client):
    cat = CategoryFactory()
    StoryboardFactory(category=cat)
    url = f"/storyboards/category/{cat.slug}/"
    resp = client.get(url)
    assert resp.status_code == 302
    assert resp.url == f"{AUTH_URL}?next={url}"


def test_detail_redirects_to_login_when_locked(client):
    sb = StoryboardFactory()
    url = f"/storyboards/{sb.slug}/"
    resp = client.get(url)
    assert resp.status_code == 302
    assert resp.url == f"{AUTH_URL}?next={url}"


# --- the login form itself is reachable while locked ---


def test_login_form_renders_with_password_field(client):
    body = client.get(AUTH_URL).content.decode()
    assert 'name="password"' in body
    assert 'type="password"' in body


# --- a correct POST unlocks; a wrong one does not ---


def test_correct_password_sets_flag_and_redirects_to_next(client):
    resp = client.post(AUTH_URL, {"password": "s3cret", "next": INDEX_URL})
    assert resp.status_code == 302
    assert resp.url == INDEX_URL
    assert client.session["storyboards_auth"] is True


def test_correct_password_with_no_next_lands_on_the_index(client):
    resp = client.post(AUTH_URL, {"password": "s3cret"})
    assert resp.status_code == 302
    assert resp.url == INDEX_URL


def test_wrong_password_shows_error_and_leaves_locked(client):
    resp = client.post(AUTH_URL, {"password": "nope", "next": INDEX_URL})
    assert resp.status_code == 200
    assert "Incorrect password." in resp.content.decode()
    assert "storyboards_auth" not in client.session
    # And the gate is still shut.
    assert client.get(INDEX_URL).status_code == 302


def test_empty_configured_password_never_unlocks(client, settings):
    # A misconfigured (unset) password must fail closed, not match a blank POST.
    settings.STORYBOARDS_PASSWORD = ""
    resp = client.post(AUTH_URL, {"password": "", "next": INDEX_URL})
    assert resp.status_code == 200
    assert "storyboards_auth" not in client.session


# --- hardening: session fixation + missing field ---


def test_successful_unlock_cycles_the_session_key(client):
    # Session fixation defence: the session id a visitor presents before auth must
    # not survive the unlock, so a pre-seeded id can't be replayed as authenticated.
    session = client.session  # seed + persist a pre-auth session
    session["seed"] = 1
    session.save()
    before = session.session_key
    client.post(AUTH_URL, {"password": "s3cret"})
    assert client.session.session_key != before
    assert client.session["storyboards_auth"] is True


def test_post_without_password_field_stays_locked(client):
    # A POST omitting the field entirely must fail closed, never crash.
    resp = client.post(AUTH_URL, {"next": INDEX_URL})
    assert resp.status_code == 200
    assert "storyboards_auth" not in client.session


# --- one unlock covers the whole namespace ---


def test_one_unlock_opens_index_category_and_detail(client):
    cat = CategoryFactory()
    sb = StoryboardFactory(category=cat)
    client.post(AUTH_URL, {"password": "s3cret"})
    assert client.get(INDEX_URL).status_code == 200
    assert client.get(f"/storyboards/category/{cat.slug}/").status_code == 200
    assert client.get(f"/storyboards/{sb.slug}/").status_code == 200


# --- session ends with the browser; logout re-locks ---


def test_successful_auth_issues_a_browser_session_cookie(client):
    # SESSION_EXPIRE_AT_BROWSER_CLOSE: the session cookie carries no max-age, so
    # the browser drops it on close. An int max-age would mean a persistent cookie.
    resp = client.post(AUTH_URL, {"password": "s3cret"})
    assert resp.cookies["sessionid"]["max-age"] == ""


def test_logout_clears_the_flag_and_relocks(client):
    _unlock(client)
    assert client.get(INDEX_URL).status_code == 200
    resp = client.post(LOGOUT_URL)
    assert resp.status_code == 302
    assert resp.url == AUTH_URL
    assert "storyboards_auth" not in client.session
    assert client.get(INDEX_URL).status_code == 302


# --- open-redirect protection on next ---


def test_external_next_is_ignored_in_favour_of_the_index(client):
    resp = client.post(
        AUTH_URL, {"password": "s3cret", "next": "https://evil.example/steal"}
    )
    assert resp.status_code == 302
    assert resp.url == INDEX_URL
