"""End-to-end coverage for drag-sortable *unsaved* inline rows (#27).

Opt-in: marked ``e2e`` and deselected by default (pytest.ini). Run with a real
browser via ``pytest -m e2e`` after ``playwright install chromium``. Strip the
storage env first, like the rest of the suite, so any upload hits the local
filesystem and not the real R2 bucket (see LEARNINGS.md).

``inline_sortable_new.js`` promotes each added row on ``formset:added`` so
sortable2's existing Sortable drives it. The seam *we* own is "a new row becomes
a drag participant in the DOM" — sortable2's drop engine is already trusted (it
works for saved rows), so this asserts the promotion, not a simulated drop:
after "Add another", each new row must carry ``has_original``, the handle
``td.original p``, and the order field ``input._reorder_`` sortable2 rewrites.
The empty-form template row is checked to have *no* handle, proving the hook —
not the server-rendered markup — is what creates it.
"""

import os

# Playwright's sync API runs an asyncio loop in this thread, tripping Django's
# async-safety guard on the (separate-thread) ORM calls. The browser is driven on
# its own thread, so there is no real concurrent DB access — opt out of the guard.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")

import re  # noqa: E402

import pytest  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402
from playwright.sync_api import expect  # noqa: E402

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

# The ComicPage FK is related_name="pages", so the inline formset prefix is
# "pages" (group id, dynamic-row class, and empty-row id all derive from it).
GROUP = "#pages-group"
NEW_ROWS = f"{GROUP} tbody tr.dynamic-pages"
EMPTY_ROW = f"{GROUP} #pages-empty"


def _login_admin(page, live_server):
    User.objects.create_superuser("admin", "admin@example.com", "password")
    page.goto(f"{live_server.url}/admin/login/")
    page.fill("#id_username", "admin")
    page.fill("#id_password", "password")
    page.click("input[type=submit]")


def test_added_comic_page_rows_become_drag_participants(live_server, page):
    _login_admin(page, live_server)
    page.goto(f"{live_server.url}/admin/portfolio/comic/add/")

    # The server-rendered template row carries no drag handle of its own — so a
    # handle on an added row can only have come from our promoter.
    expect(page.locator(f"{EMPTY_ROW} td.original p")).to_have_count(0)

    add_another = page.locator(f"{GROUP} .add-row a")
    add_another.click()
    add_another.click()

    new_rows = page.locator(NEW_ROWS)
    expect(new_rows).to_have_count(2)
    for i in range(2):
        row = new_rows.nth(i)
        # Promoted into sortable2's "original" set (its live selectors then grab,
        # move, and renumber it)...
        expect(row).to_have_class(re.compile(r"\bhas_original\b"))
        # ...with a grip to grab (the CSS draws it on td.original p)...
        expect(row.locator("td.original p")).to_have_count(1)
        # ...and the order field sortable2 writes the new position into on drop.
        expect(row.locator("input._reorder_")).to_have_count(1)
