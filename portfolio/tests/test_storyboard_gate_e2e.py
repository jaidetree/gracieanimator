"""End-to-end coverage for the storyboard password gate (Slice 9).

Opt-in: marked ``e2e`` and deselected by default (pytest.ini). Run with a real
browser via ``pytest -m e2e`` after ``playwright install chromium``. Strip the
storage env first, like the rest of the suite, so factory uploads hit the local
filesystem and not the real R2 bucket (see LEARNINGS.md).

Unlike the HTTP-seam tests, this can't lean on ``override_settings`` — the
``live_server`` thread reads settings independently — so it uses the shared
password baked into ``config.test_settings`` and the real CSRF round-trip.
"""

import os

# Playwright's sync API runs an asyncio loop in this thread, tripping Django's
# async-safety guard on the (separate-thread) ORM calls. The browser is driven on
# its own thread, so there is no real concurrent DB access — opt out of the guard.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")

import pytest  # noqa: E402
from django.conf import settings  # noqa: E402
from playwright.sync_api import expect  # noqa: E402

from portfolio.tests.factories import StoryboardFactory  # noqa: E402

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]


def test_prompt_enter_unlocks_then_logout_relocks(live_server, page):
    sb = StoryboardFactory(title="Gated Board")
    index_url = f"{live_server.url}/storyboards/"

    # A locked visit lands on the login form, not the storyboards.
    page.goto(index_url)
    expect(page).to_have_url(f"{live_server.url}/auth/?next=/storyboards/")
    expect(page.locator('input[name="password"]')).to_be_visible()

    # Entering the password unlocks the session and returns to the index.
    page.fill('input[name="password"]', settings.STORYBOARDS_PASSWORD)
    page.click("button[type=submit]")
    expect(page).to_have_url(index_url)
    expect(page.get_by_text("Gated Board")).to_be_visible()

    # The unlock is session-wide: a second storyboard URL opens without re-entry.
    page.goto(f"{live_server.url}/storyboards/{sb.slug}/")
    expect(page).to_have_url(f"{live_server.url}/storyboards/{sb.slug}/")

    # Logging out re-locks: the index bounces back to the login form.
    page.goto(index_url)
    page.click("button.storyboards__logout")
    expect(page).to_have_url(f"{live_server.url}/auth/")
    page.goto(index_url)
    expect(page).to_have_url(f"{live_server.url}/auth/?next=/storyboards/")
