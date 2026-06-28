import pytest

from portfolio.tests.factories import (
    IllustrationFactory,
    SketchbookSampleFactory,
    make_comic,
)

pytestmark = pytest.mark.django_db

HOME_URL = "/"


def _body(client):
    return client.get(HOME_URL).content.decode()


# --- one featured, published piece per type (HTTP seam) ---

def test_featured_piece_appears(client):
    shown = IllustrationFactory(title="Hero", featured=True, published=True)
    assert shown.title in _body(client)


def test_only_one_piece_per_type_even_when_several_featured(client):
    # Lowest-order featured piece wins; the rest of the type are not shown.
    chosen = IllustrationFactory(title="Chosen", featured=True, published=True, order=1)
    other = IllustrationFactory(title="Runner Up", featured=True, published=True, order=2)
    body = _body(client)
    assert chosen.title in body
    assert other.title not in body


# --- published + featured filtering (HTTP seam) ---

def test_unpublished_featured_never_selected(client):
    draft = IllustrationFactory(title="Draft", featured=True, published=False)
    assert draft.title not in _body(client)


def test_published_but_not_featured_never_selected(client):
    plain = IllustrationFactory(title="Plain", featured=False, published=True)
    assert plain.title not in _body(client)


# --- cross-model ordering (HTTP seam) ---

def test_orders_illustration_then_sketchbook_then_comic(client):
    # Storyboards (Slice 8, #10) aren't modeled yet, so they're absent; the
    # remaining three keep their canonical relative order.
    illo = IllustrationFactory(title="Featured Illo", featured=True, published=True)
    sketch = SketchbookSampleFactory(title="Featured Sketch", featured=True, published=True)
    comic = make_comic(title="Featured Comic", featured=True, published=True)
    body = _body(client)
    assert body.index(illo.title) < body.index(sketch.title) < body.index(comic.title)


# --- thumbnails link to section pages (HTTP seam) ---

def test_each_thumbnail_links_to_its_section_page(client):
    IllustrationFactory(featured=True, published=True)
    SketchbookSampleFactory(featured=True, published=True)
    make_comic(featured=True, published=True)
    body = _body(client)
    assert 'href="/illustrations/"' in body
    assert 'href="/sketchbook-samples/"' in body
    assert 'href="/comics/"' in body


def test_thumbnail_uses_derived_rendition(client):
    illo = IllustrationFactory(featured=True, published=True)
    assert illo.thumbnail_rendition.url in _body(client)


# --- graceful fallback (HTTP seam) ---

def test_type_without_featured_piece_is_omitted(client):
    # Only an illustration is featured; sketchbook/comic contribute nothing and
    # the page still renders.
    illo = IllustrationFactory(title="Lonely", featured=True, published=True)
    resp = client.get(HOME_URL)
    assert resp.status_code == 200
    body = resp.content.decode()
    assert illo.title in body
    assert 'href="/sketchbook-samples/"' not in body
    assert 'href="/comics/"' not in body


def test_homepage_with_no_featured_pieces_still_renders(client):
    IllustrationFactory(featured=False, published=True)
    resp = client.get(HOME_URL)
    assert resp.status_code == 200
    assert "Nothing here yet." in resp.content.decode()
