"""End-to-end coverage for the in-place comic page-swapper.

Opt-in: marked ``e2e`` and deselected by default (pytest.ini). Run with a real
browser via ``pytest -m e2e`` after ``playwright install chromium``. Strip the
storage env first, exactly like the rest of the suite, so factory image uploads
hit the local filesystem and not the real R2 bucket (see LEARNINGS.md):

    env -u DATABASE_URL -u R2_BUCKET_NAME -u R2_ACCESS_KEY_ID \\
        -u R2_SECRET_ACCESS_KEY -u R2_ENDPOINT_URL -u R2_CUSTOM_DOMAIN \\
        pytest -m e2e

``live_server`` serves the app on a real socket; ``transaction=True`` commits the
factory rows so the server thread (a separate DB connection) can see them.
"""

import os

# Playwright's sync API runs an asyncio loop in this thread, which trips Django's
# async-safety guard on the (separate-thread) ORM calls. The browser is driven on
# its own thread, so there is no real concurrent DB access — opt out of the guard.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")

import pytest  # noqa: E402
from playwright.sync_api import expect  # noqa: E402

from portfolio.tests.factories import make_comic  # noqa: E402

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

LARGE_IMAGE = "img.comic__page-large"


def _wait_for_alpine(page):
    """The Alpine script is deferred; reactivity only works once it has loaded."""
    page.wait_for_function("() => window.Alpine !== undefined")


def test_next_swaps_the_page_in_place_and_pushes_the_url(live_server, page):
    comic = make_comic(n_pages=3)
    page.goto(f"{live_server.url}/comics/{comic.slug}/")
    _wait_for_alpine(page)

    # Sentinels: a window flag (wiped by any full reload) and a property on the
    # <h1>, which lives *outside* #comic-viewer. Both surviving proves the swap
    # was both reload-free and scoped to the viewer, not the whole document.
    page.evaluate("window.__noReload = true")
    page.evaluate("document.querySelector('h1').__kept = true")
    page_one_src = page.get_attribute(LARGE_IMAGE, "src")

    page.click("a.comic__next")

    # The href was pushed onto history: the URL is shareable/deep-linkable.
    expect(page).to_have_url(f"{live_server.url}/comics/{comic.slug}/page/2/")
    # The large image was swapped to the next page...
    expect(page.locator(LARGE_IMAGE)).not_to_have_attribute("src", page_one_src)
    # ...without a full reload (window survived)...
    assert page.evaluate("() => window.__noReload === true")
    # ...and without replacing anything outside the viewer (the <h1> is the same
    # element, keeping its tagged property).
    assert page.evaluate("() => document.querySelector('h1').__kept === true")


def test_previous_swaps_back_in_place(live_server, page):
    comic = make_comic(n_pages=3)
    page.goto(f"{live_server.url}/comics/{comic.slug}/page/2/")
    _wait_for_alpine(page)
    page.evaluate("window.__noReload = true")

    page.click("a.comic__prev")

    # Page 1's canonical URL is the bare detail URL.
    expect(page).to_have_url(f"{live_server.url}/comics/{comic.slug}/")
    assert page.evaluate("() => window.__noReload === true")


def test_direct_page_url_is_deep_linkable(live_server, page):
    # The no-JS server route also drives selection, so a shared URL lands deep.
    comic = make_comic(n_pages=3)
    page.goto(f"{live_server.url}/comics/{comic.slug}/page/3/")
    # The last page has a previous chevron but no next one.
    expect(page.locator("a.comic__prev")).to_be_visible()
    expect(page.locator("a.comic__next")).to_be_hidden()
