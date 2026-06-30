"""Illustration-specific behaviour.

The gallery layout, ordering, rendition, and published-filtering guarantees are
shared with SketchbookSample and live in ``test_galleries.py``; this suite covers
what's particular to Illustration — slug generation on the shared base, the
alpha-PNG rendition path, and thumbnail fallback.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from portfolio.tests.factories import IllustrationFactory, jpeg_bytes, png_rgba_bytes

pytestmark = pytest.mark.django_db

GALLERY_URL = "/illustrations/"


# --- slug generation (model save() seam) ---


def test_slug_auto_generated_from_title():
    illo = IllustrationFactory(title="Sunset Over Water", slug="")
    assert illo.slug == "sunset-over-water"


def test_explicit_slug_is_not_overwritten():
    illo = IllustrationFactory(title="Sunset", slug="custom-url")
    assert illo.slug == "custom-url"


def test_slug_is_unique_within_type():
    first = IllustrationFactory(title="Portrait", slug="")
    second = IllustrationFactory(title="Portrait", slug="")
    assert first.slug == "portrait"
    assert second.slug == "portrait-2"


# --- alpha-source rendition (HTTP seam) ---


def test_gallery_renders_transparent_png_source(client):
    # An illustrator may upload an RGBA PNG; the JPEG rendition must not 500.
    png = SimpleUploadedFile("alpha.png", png_rgba_bytes(), content_type="image/png")
    illo = IllustrationFactory(published=True, image=png)
    resp = client.get(GALLERY_URL)
    assert resp.status_code == 200
    # Generating the rendition lazily must succeed for an alpha source.
    assert illo.gallery_image.url in resp.content.decode()


# --- thumbnail fallback (model seam) ---


def test_thumbnail_auto_derives_from_image_when_blank():
    illo = IllustrationFactory()
    assert not illo.thumbnail
    assert illo.thumbnail_url == illo.thumbnail_rendition.url


def test_manual_thumbnail_wins():
    manual = SimpleUploadedFile("thumb.jpg", jpeg_bytes(), content_type="image/jpeg")
    illo = IllustrationFactory(thumbnail=manual)
    assert illo.thumbnail_url == illo.thumbnail.url
    assert illo.thumbnail_url != illo.thumbnail_rendition.url
