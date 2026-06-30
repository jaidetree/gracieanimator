"""Brute-force lockout on the Django admin login (Slice 32, django-axes).

The admin login fronts full content control, so a credential-stuffing grind must
hit a wall. axes locks the username+IP *combination* after a few failures, with an
hour cool-off. These tests drive the real `/admin/login/` POST — the auth seam
axes hooks — not a settings assertion.

Lockout is off in the default test settings (so the many-POST admin suites don't
lock themselves out); each test opts back in via the `axes_on` fixture. Per
LEARNINGS axes writes to the DB, so run env-stripped:
`./scripts/test.sh portfolio/tests/test_admin_login_lockout.py`.
"""

import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db

LOGIN_URL = "/admin/login/"
PASSWORD = "right-password"
USERNAME = "gracie"
# AXES_FAILURE_LIMIT is 5: the 6th failed attempt for a key is the first blocked.
LIMIT = 5
# Distinct documentation-range IPs (RFC 5737) keep each key's bucket isolated.
IP_A = "203.0.113.7"
IP_B = "198.51.100.4"


@pytest.fixture
def axes_on(settings):
    """Enable lockout for this test against a clean attempt log.

    axes state lives in its DB tables, rolled back with the test transaction, so
    there's no global state to clean up; `reset_attempts` is belt-and-suspenders.
    """
    from axes.handlers.proxy import AxesProxyHandler

    settings.AXES_ENABLED = True
    AxesProxyHandler.reset_attempts()


@pytest.fixture
def admin_user(db):
    return get_user_model().objects.create_superuser(
        USERNAME, "gracie@example.com", PASSWORD
    )


def _bad_login(client, ip, username=USERNAME):
    return client.post(
        LOGIN_URL,
        {"username": username, "password": "wrong"},
        HTTP_X_FORWARDED_FOR=ip,
    )


def _good_login(client, ip, username=USERNAME):
    return client.post(
        LOGIN_URL,
        {"username": username, "password": PASSWORD},
        HTTP_X_FORWARDED_FOR=ip,
    )


# --- the limit binds: a wrong-password grind eventually locks out ---


def test_repeated_bad_logins_eventually_lock_out(client, axes_on, admin_user):
    statuses = [_bad_login(client, IP_A).status_code for _ in range(LIMIT + 1)]
    # Assert the transition, not an exact boundary index: early misses re-render
    # the form (200), the over-limit attempt is blocked (429).
    assert statuses[0] == 200
    assert statuses[-1] == 429


def test_lockout_fails_closed_even_with_the_correct_password(
    client, axes_on, admin_user
):
    for _ in range(LIMIT + 1):
        _bad_login(client, IP_A)
    resp = _good_login(client, IP_A)
    assert resp.status_code == 429  # the right password is refused while locked
    assert "_auth_user_id" not in client.session  # and no session was established


def test_lockout_shows_a_friendly_message_not_a_stack_trace(
    client, axes_on, admin_user
):
    for _ in range(LIMIT + 1):
        _bad_login(client, IP_A)
    blocked = _bad_login(client, IP_A)
    assert blocked.status_code == 429
    body = blocked.content.decode()
    assert "Account locked" in body
    assert "Traceback" not in body


# --- a correct login under the limit works and resets the failure count ---


def test_correct_login_under_the_limit_succeeds(client, axes_on, admin_user):
    resp = _good_login(client, IP_A)
    assert resp.status_code == 302  # admin redirects to the index on success
    assert client.session["_auth_user_id"] == str(admin_user.pk)


def test_a_successful_login_resets_the_failure_count(client, axes_on, admin_user):
    for _ in range(LIMIT - 1):  # one short of the limit
        _bad_login(client, IP_A)
    assert _good_login(client, IP_A).status_code == 302  # succeeds, clears the count
    client.logout()  # else admin/login redirects an authed client without checking

    # Were the count not reset, these would push the total past the limit and lock
    # out; because the success cleared it, every one re-renders the form.
    statuses = [_bad_login(client, IP_A).status_code for _ in range(LIMIT - 1)]
    assert statuses == [200] * (LIMIT - 1)


# --- the lock keys on username AND IP, not either alone ---


def test_lock_is_scoped_to_the_ip_not_the_username_alone(client, axes_on, admin_user):
    # Lock (gracie, IP_A), then the same username from a different IP is unaffected
    # — so a single account can't be locked out from anywhere at once (admin DoS).
    for _ in range(LIMIT + 1):
        _bad_login(client, IP_A)
    assert _bad_login(client, IP_A).status_code == 429  # locked on IP_A
    assert _bad_login(client, IP_B).status_code == 200  # but free from IP_B


def test_lock_is_scoped_to_the_username_not_the_ip_alone(client, axes_on, admin_user):
    # Lock (gracie, IP_A), then a different username from the same IP is unaffected
    # — so one bad actor doesn't lock innocent users sharing the IP.
    for _ in range(LIMIT + 1):
        _bad_login(client, IP_A)
    assert _bad_login(client, IP_A).status_code == 429  # gracie is locked
    assert _bad_login(client, IP_A, username="someone-else").status_code == 200
