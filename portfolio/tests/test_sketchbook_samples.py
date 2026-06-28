import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from portfolio.tests.factories import SketchbookSampleFactory

pytestmark = pytest.mark.django_db

GALLERY_URL = "/sketchbook-samples/"


# --- inheritance from the Project base (model seam) ---
# Slug generation/uniqueness lives on the shared base and is exercised by the
# Illustration suite; here we only confirm the chain resolves for this type.

def test_slug_auto_generated_from_title():
    sample = SketchbookSampleFactory(title="Morning Studies", slug="")
    assert sample.slug == "morning-studies"


# --- published filtering (HTTP seam) ---

def test_only_published_samples_appear(client):
    shown = SketchbookSampleFactory(title="Visible Sketch", published=True)
    hidden = SketchbookSampleFactory(title="Hidden Sketch", published=False)
    body = client.get(GALLERY_URL).content.decode()
    assert shown.title in body
    assert hidden.title not in body


# --- gallery layout (HTTP seam) ---

def test_gallery_is_single_column_full_width(client):
    SketchbookSampleFactory(published=True)
    body = client.get(GALLERY_URL).content.decode()
    # Single-column stack (flex-col), images at container width (w-full), no grid.
    assert "flex-col" in body
    assert "w-full" in body
    assert "grid-cols" not in body


def test_gallery_orders_by_order_field(client):
    SketchbookSampleFactory(title="Second", order=2, published=True)
    SketchbookSampleFactory(title="First", order=1, published=True)
    body = client.get(GALLERY_URL).content.decode()
    assert body.index("First") < body.index("Second")


def test_gallery_serves_rendition_not_original(client):
    sample = SketchbookSampleFactory(published=True)
    body = client.get(GALLERY_URL).content.decode()
    assert sample.gallery_image.url in body
    assert sample.image.url not in body


# --- thumbnail fallback (model seam) ---

def test_thumbnail_auto_derives_from_image_when_blank():
    sample = SketchbookSampleFactory()
    assert not sample.thumbnail
    assert sample.thumbnail_url == sample.thumbnail_rendition.url


def test_manual_thumbnail_wins():
    manual = SimpleUploadedFile("thumb.jpg", _jpeg_bytes(), content_type="image/jpeg")
    sample = SketchbookSampleFactory(thumbnail=manual)
    assert sample.thumbnail_url == sample.thumbnail.url
    assert sample.thumbnail_url != sample.thumbnail_rendition.url


# --- helpers ---

def _jpeg_bytes():
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, "JPEG")
    return buf.getvalue()
