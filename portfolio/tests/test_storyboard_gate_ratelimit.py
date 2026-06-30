"""Rate-limit tests for the storyboard password gate (Slice 31).

The gate throttles `POST /auth/` to a few attempts per client IP per minute so the
shared secret can't be brute-forced at dyno speed. Rate limiting is off in the
default test settings (so the #30 gate suites' many POSTs don't trip it); these
tests opt back in per-test and drive the real DB cache the limiter counts in.

Per LEARNINGS the limiter writes to the DB cache table (`createcachetable`), so
run env-stripped: `./scripts/test.sh portfolio/tests/test_storyboard_gate_ratelimit.py`.
"""

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.test import RequestFactory

from portfolio import storyboard_gate

pytestmark = pytest.mark.django_db

AUTH_URL = "/auth/"
INDEX_URL = "/storyboards/"
PASSWORD = "s3cret"
# AUTH_RATE is "5/m": the 6th POST in the window is the first blocked one.
LIMIT = 5
# Distinct, documentation-range client IPs (RFC 5737) keep each test's bucket
# isolated even within one cache window — no cross-test bleed.
IP_A = "203.0.113.7"
IP_B = "198.51.100.4"


@pytest.fixture(autouse=True)
def password(settings):
    settings.STORYBOARDS_PASSWORD = PASSWORD


@pytest.fixture
def ratelimited(settings):
    """Enable rate limiting against a clean DB cache, for this test only.

    `createcachetable` runs inside the test's rolled-back transaction (Postgres
    DDL is transactional), so the `ratelimit_cache` table exists for the duration
    and disappears with the rollback — the real seam, no global state to clean up.
    """
    call_command("createcachetable")
    cache.clear()
    settings.RATELIMIT_ENABLE = True


def _wrong_post(client, ip):
    return client.post(
        AUTH_URL, {"password": "nope", "next": INDEX_URL}, HTTP_X_FORWARDED_FOR=ip
    )


# --- the key function: trust only the hop Heroku appends ---


def test_client_ip_key_uses_the_last_forwarded_hop():
    # Earlier XFF entries are client-supplied and spoofable; the last is Heroku's.
    request = RequestFactory().post(
        AUTH_URL, HTTP_X_FORWARDED_FOR="1.2.3.4, 9.9.9.9, 203.0.113.7"
    )
    assert storyboard_gate.client_ip_key("g", request) == "203.0.113.7"


def test_client_ip_key_falls_back_to_remote_addr_without_xff():
    request = RequestFactory().post(AUTH_URL, REMOTE_ADDR="127.0.0.1")
    assert storyboard_gate.client_ip_key("g", request) == "127.0.0.1"


# --- the limit binds: wrong-password grind eventually blocks ---


def test_repeated_wrong_password_eventually_blocks(client, ratelimited):
    statuses = [_wrong_post(client, IP_A).status_code for _ in range(LIMIT + 1)]
    # Assert the transition, not an exact boundary index: early attempts get the
    # form back (200), the over-limit attempt is blocked (429).
    assert statuses[0] == 200
    assert statuses[-1] == 429
    assert "storyboards_auth" not in client.session


def test_block_renders_a_friendly_message_not_a_stack_trace(client, ratelimited):
    for _ in range(LIMIT):
        _wrong_post(client, IP_A)
    blocked = _wrong_post(client, IP_A)
    assert blocked.status_code == 429
    body = blocked.content.decode()
    assert "Too many attempts" in body
    assert "Traceback" not in body


# --- the limit is per client IP ---


def test_a_second_ip_is_unaffected_within_the_same_window(client, ratelimited):
    for _ in range(LIMIT + 1):
        _wrong_post(client, IP_A)
    assert _wrong_post(client, IP_A).status_code == 429  # IP_A is blocked
    assert _wrong_post(client, IP_B).status_code == 200  # IP_B still gets the form


# --- a correct password under the limit still unlocks (no regression) ---


def test_correct_password_under_the_limit_unlocks(client, ratelimited):
    resp = client.post(AUTH_URL, {"password": PASSWORD}, HTTP_X_FORWARDED_FOR=IP_A)
    assert resp.status_code == 302
    assert resp.url == INDEX_URL
    assert client.session["storyboards_auth"] is True


# --- a blocked request fails closed even with the correct password ---


def test_block_fails_closed_even_with_the_correct_password(client, ratelimited):
    for _ in range(LIMIT):
        _wrong_post(client, IP_A)
    resp = client.post(AUTH_URL, {"password": PASSWORD}, HTTP_X_FORWARDED_FOR=IP_A)
    assert resp.status_code == 429
    assert "storyboards_auth" not in client.session
