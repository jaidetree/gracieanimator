"""HTTP-seam tests for the public storyboard views (Slice 10).

Covers the index-by-category grouping, the per-category listing, detail
composition (videos, decks, PDFs, body + section nav), the small-rendition grid,
and published filtering. The oembed boundary is stubbed by the autouse
``stub_oembed`` fixture, so factory-built media carry cached embed HTML; the
"no request-time oembed" test swaps ``fetch`` for a spy after the rows exist.

The views are now behind the storyboard password gate (Slice 9): the autouse
``unlock_storyboards`` fixture sets the session flag so these tests exercise the
content as an unlocked visitor. The gate itself (locked/unlocked, login, logout)
is covered separately in ``test_storyboard_gate.py``.
"""

from unittest.mock import Mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from portfolio import oembed
from portfolio.tests.factories import (
    CategoryFactory,
    StoryboardDeckFactory,
    StoryboardFactory,
    StoryboardPDFFactory,
    StoryboardVideoFactory,
    jpeg_bytes,
)

pytestmark = pytest.mark.django_db

INDEX_URL = "/storyboards/"


@pytest.fixture(autouse=True)
def unlock_storyboards(client):
    """Unlock the gate for the shared ``client`` so these view tests see content,
    not the login redirect. The gate's own behaviour lives in test_storyboard_gate."""
    session = client.session
    session["storyboards_auth"] = True
    session.save()


def _body(client, url):
    return client.get(url).content.decode()


# --- index: grouped by category, grid beneath each heading ---


def test_index_groups_storyboards_under_their_category_headings(client):
    alpha = CategoryFactory(name="Alpha")
    beta = CategoryFactory(name="Beta")
    a = StoryboardFactory(category=alpha, title="A Board")
    b = StoryboardFactory(category=beta, title="B Board")
    body = _body(client, INDEX_URL)
    # Each category links to its own page and each storyboard to its detail.
    assert f'href="/storyboards/category/{alpha.slug}/"' in body
    assert f'href="/storyboards/category/{beta.slug}/"' in body
    assert f'href="/storyboards/{a.slug}/"' in body
    assert f'href="/storyboards/{b.slug}/"' in body
    # Storyboard sits beneath its category heading (by name, A before B).
    assert body.index("Alpha") < body.index("A Board") < body.index("Beta")


def test_index_omits_categories_with_no_published_storyboards(client):
    empty = CategoryFactory(name="Empty Cat")
    StoryboardFactory(category=empty, published=False)
    body = _body(client, INDEX_URL)
    assert "Empty Cat" not in body


def test_index_shows_only_published_storyboards(client):
    shown = StoryboardFactory(title="Shown Board", published=True)
    hidden = StoryboardFactory(title="Hidden Board", published=False)
    body = _body(client, INDEX_URL)
    assert shown.title in body
    assert hidden.title not in body


# --- category page: a single category's grid ---


def test_category_page_lists_only_that_categorys_storyboards(client):
    alpha = CategoryFactory(name="Alpha")
    beta = CategoryFactory(name="Beta")
    mine = StoryboardFactory(category=alpha, title="Mine")
    other = StoryboardFactory(category=beta, title="Other")
    body = _body(client, f"/storyboards/category/{alpha.slug}/")
    assert mine.title in body
    assert other.title not in body


def test_category_page_shows_only_published(client):
    cat = CategoryFactory(name="Cat")
    shown = StoryboardFactory(category=cat, title="Shown", published=True)
    hidden = StoryboardFactory(category=cat, title="Hidden", published=False)
    body = _body(client, f"/storyboards/category/{cat.slug}/")
    assert shown.title in body
    assert hidden.title not in body


def test_category_page_links_back_to_the_index(client):
    cat = CategoryFactory()
    StoryboardFactory(category=cat)
    body = _body(client, f"/storyboards/category/{cat.slug}/")
    assert f'href="{INDEX_URL}"' in body


def test_unknown_category_404(client):
    assert client.get("/storyboards/category/nope/").status_code == 404


# --- grids use small renditions (manual-thumbnail case) ---


def test_grid_uses_small_rendition_not_full_thumbnail(client):
    thumb = SimpleUploadedFile("t.jpg", jpeg_bytes(), content_type="image/jpeg")
    sb = StoryboardFactory(thumbnail=thumb)
    body = _body(client, INDEX_URL)
    # The small grid rendition is served; the full uploaded thumbnail is not.
    assert sb.thumbnail_rendition.url in body
    assert sb.thumbnail.url not in body


# --- detail: composes videos, decks, PDFs, body + section nav ---


def _detail_url(sb):
    return f"/storyboards/{sb.slug}/"


def test_detail_composes_videos_decks_pdfs_and_body(client):
    sb = StoryboardFactory(body="<p>Body words here</p>")
    video = StoryboardVideoFactory(storyboard=sb, url="https://vimeo.com/1")
    deck = StoryboardDeckFactory(storyboard=sb, url="https://speakerdeck.com/u/t")
    pdf = StoryboardPDFFactory(storyboard=sb, display_name="The Brief")
    video.refresh_from_db()
    deck.refresh_from_db()
    body = _body(client, _detail_url(sb))
    assert video.embed_html in body  # cached video embed
    assert deck.embed_html in body  # cached deck embed
    assert pdf.display_name in body and pdf.file.url in body  # downloadable PDF
    assert "Body words here" in body  # rich body rendered


def test_detail_renders_media_embed_in_body(client):
    """A media embed authored into the WYSIWYG body (Slice 12) reaches the public
    page as a working iframe, surviving both the save-time sanitize and render."""
    sb = StoryboardFactory(
        body=(
            '<figure class="media"><div data-oembed-url="https://youtu.be/z">'
            '<iframe src="https://www.youtube.com/embed/z"></iframe></div></figure>'
        )
    )
    body = _body(client, _detail_url(sb))
    assert '<iframe src="https://www.youtube.com/embed/z">' in body


def test_detail_renders_cached_embed_dimensions(client):
    sb = StoryboardFactory()
    video = StoryboardVideoFactory(storyboard=sb, url="https://vimeo.com/9")
    video.refresh_from_db()
    body = _body(client, _detail_url(sb))
    # Stub dims are 1280x720 -> padding-bottom 56% (720/1280*100, truncated).
    assert "padding-bottom: 56%" in body


def test_detail_section_nav_lists_only_present_sections(client):
    sb = StoryboardFactory(body="")
    StoryboardVideoFactory(storyboard=sb, url="https://vimeo.com/1")
    body = _body(client, _detail_url(sb))
    # Only the animatic exists: its anchor is present, the others are not.
    assert 'href="#animatic"' in body
    assert 'href="#boards"' not in body
    assert 'href="#pdfs"' not in body
    assert 'href="#content"' not in body


def test_detail_section_nav_includes_every_present_section(client):
    sb = StoryboardFactory(body="<p>more</p>")
    StoryboardVideoFactory(storyboard=sb, url="https://vimeo.com/1")
    StoryboardDeckFactory(storyboard=sb, url="https://speakerdeck.com/u/t")
    StoryboardPDFFactory(storyboard=sb)
    body = _body(client, _detail_url(sb))
    for anchor in ("#animatic", "#boards", "#pdfs", "#content"):
        assert f'href="{anchor}"' in body


def test_detail_renders_without_a_video(client):
    # A thumbnail-only storyboard (no video) is valid; detail still renders.
    thumb = SimpleUploadedFile("t.jpg", jpeg_bytes(), content_type="image/jpeg")
    sb = StoryboardFactory(title="Quiet Board", thumbnail=thumb)
    body = _body(client, _detail_url(sb))
    assert "Quiet Board" in body
    assert "<iframe" not in body  # no empty embed emitted


def test_detail_makes_no_request_time_oembed_call(client, monkeypatch):
    sb = StoryboardFactory()
    StoryboardVideoFactory(storyboard=sb, url="https://vimeo.com/1")
    spy = Mock()
    monkeypatch.setattr(oembed, "fetch", spy)  # after the row is created
    client.get(_detail_url(sb))
    spy.assert_not_called()


def test_unpublished_storyboard_detail_404(client):
    sb = StoryboardFactory(published=False)
    assert client.get(_detail_url(sb)).status_code == 404
