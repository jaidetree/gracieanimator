"""Shared gallery-page behaviour for the single-column image galleries.

Illustration and SketchbookSample render through the same gallery template (a
wrapping thumbnail grid with a lightbox dialog) and inherit the same
``Project`` base, so the published-filtering, layout, ordering, and rendition
guarantees are identical — exercised here once, parametrized over both types.
Type-specific behaviour (slug rules, alpha-PNG renditions, thumbnail fallback)
stays in each type's own suite.
"""

import pytest

from portfolio.tests.factories import IllustrationFactory, SketchbookSampleFactory

pytestmark = pytest.mark.django_db

GALLERIES = [
    pytest.param(IllustrationFactory, "/illustrations/", id="illustrations"),
    pytest.param(SketchbookSampleFactory, "/sketchbook-samples/", id="sketchbook"),
]


@pytest.mark.parametrize("factory,url", GALLERIES)
def test_only_published_pieces_appear(client, factory, url):
    shown = factory(title="Visible", published=True)
    hidden = factory(title="Hidden", published=False)
    body = client.get(url).content.decode()
    assert shown.title in body
    assert hidden.title not in body


@pytest.mark.parametrize("factory,url", GALLERIES)
def test_gallery_is_wrapping_thumbnail_grid(client, factory, url):
    factory(published=True)
    body = client.get(url).content.decode()
    # Wrapping flexbox thumbnail grid with a lightbox dialog, not a CSS grid.
    assert "flex-wrap" in body
    assert "gallery-dialog" in body
    assert "grid-cols" not in body


@pytest.mark.parametrize("factory,url", GALLERIES)
def test_gallery_orders_by_order_field(client, factory, url):
    factory(title="Second", order=2, published=True)
    factory(title="First", order=1, published=True)
    body = client.get(url).content.decode()
    assert body.index("First") < body.index("Second")


@pytest.mark.parametrize("factory,url", GALLERIES)
def test_gallery_serves_rendition_not_original(client, factory, url):
    piece = factory(published=True)
    body = client.get(url).content.decode()
    assert piece.gallery_image.url in body
    assert piece.image.url not in body
