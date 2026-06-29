"""Breadcrumb trails across the portfolio pages (Slice 26).

One ``_breadcrumb.html`` partial renders the ancestor trail above each page
title: the current page's own title stays in the ``<h1>`` and never appears as a
crumb, every crumb is followed by a slash, and labels render lowercase. These
tests drive the HTTP seam and read the rendered trail back through ``crumbs``.
The gated storyboard pages run unlocked (see ``unlock_storyboards``).
"""

import re

import pytest

from pages.tests.factories import PageFactory
from portfolio.tests.factories import (
    CategoryFactory,
    ComicFactory,
    ComicPageFactory,
    IllustrationFactory,
    SketchbookSampleFactory,
    StoryboardFactory,
    StoryboardVideoFactory,
)

pytestmark = pytest.mark.django_db

_NAV_RE = re.compile(
    r'<nav class="breadcrumb[^"]*" aria-label="Breadcrumb">(.*?)</nav>', re.S
)
_CRUMB_RE = re.compile(r'<a href="([^"]+)"[^>]*>([^<]+)</a>')


def crumbs(html):
    """The ``(href, label)`` pairs of the breadcrumb nav, ``[]`` when absent."""
    nav = _NAV_RE.search(html)
    return _CRUMB_RE.findall(nav.group(1)) if nav else []


@pytest.fixture
def unlock_storyboards(client):
    """Unlock the storyboard gate so the gated pages render their content."""
    session = client.session
    session["storyboards_auth"] = True
    session.save()


PORTFOLIO = ("/", "portfolio")


def test_comics_index_trails_to_portfolio(client):
    assert crumbs(client.get("/comics/").content.decode()) == [PORTFOLIO]


def test_comic_detail_trails_through_comics(client):
    comic = ComicFactory()
    ComicPageFactory(comic=comic)
    body = client.get(f"/comics/{comic.slug}/").content.decode()
    assert crumbs(body) == [PORTFOLIO, ("/comics/", "comics")]
    # The comic's own title is the heading, not a crumb.
    assert (f"/comics/{comic.slug}/", comic.title) not in crumbs(body)


def test_illustration_gallery_trails_to_portfolio(client):
    IllustrationFactory()
    assert crumbs(client.get("/illustrations/").content.decode()) == [PORTFOLIO]


def test_sketchbook_gallery_trails_to_portfolio(client):
    SketchbookSampleFactory()
    body = client.get("/sketchbook-samples/").content.decode()
    assert crumbs(body) == [PORTFOLIO]


def test_storyboards_index_trails_to_portfolio(client, unlock_storyboards):
    assert crumbs(client.get("/storyboards/").content.decode()) == [PORTFOLIO]


def test_storyboard_category_trails_through_storyboards(client, unlock_storyboards):
    category = CategoryFactory(name="Commercials")
    StoryboardFactory(category=category)
    body = client.get(f"/storyboards/category/{category.slug}/").content.decode()
    assert crumbs(body) == [PORTFOLIO, ("/storyboards/", "storyboards")]


def test_storyboard_detail_trails_through_lowercased_category(
    client, unlock_storyboards
):
    category = CategoryFactory(name="Commercials")
    storyboard = StoryboardFactory(category=category)
    StoryboardVideoFactory(storyboard=storyboard)
    body = client.get(f"/storyboards/{storyboard.slug}/").content.decode()
    assert crumbs(body) == [
        PORTFOLIO,
        ("/storyboards/", "storyboards"),
        (f"/storyboards/category/{category.slug}/", "commercials"),
    ]


def test_home_has_no_breadcrumb(client):
    assert crumbs(client.get("/").content.decode()) == []


def test_static_page_has_no_breadcrumb(client):
    PageFactory(title="About", slug="about", published=True)
    assert crumbs(client.get("/about/").content.decode()) == []
