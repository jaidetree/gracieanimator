"""Shared gallery-page behaviour for the single-column image galleries.

Illustration and SketchbookSample render through the same gallery template and
inherit the same ``Project`` base, so the published-filtering, layout, ordering,
and rendition guarantees are identical — exercised here once, parametrized over
both types. Type-specific behaviour (slug rules, alpha-PNG renditions, thumbnail
fallback) stays in each type's own suite.
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
def test_gallery_is_single_column_full_width(client, factory, url):
    factory(published=True)
    body = client.get(url).content.decode()
    # Single-column stack (flex-col), images at container width (w-full), no grid.
    assert "flex-col" in body
    assert "w-full" in body
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
