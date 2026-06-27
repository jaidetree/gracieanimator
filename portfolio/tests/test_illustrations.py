import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from portfolio.models import Illustration
from portfolio.tests.factories import IllustrationFactory

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


# --- published filtering (HTTP seam) ---

def test_only_published_illustrations_appear(client):
    shown = IllustrationFactory(title="Visible", published=True)
    hidden = IllustrationFactory(title="Hidden", published=False)
    body = client.get(GALLERY_URL).content.decode()
    assert shown.title in body
    assert hidden.title not in body


def test_unpublished_illustration_absent(client):
    IllustrationFactory(title="Draft Piece", published=False)
    assert "Draft Piece" not in client.get(GALLERY_URL).content.decode()


# --- gallery layout (HTTP seam) ---

def test_gallery_is_single_column_full_width(client):
    IllustrationFactory(published=True)
    body = client.get(GALLERY_URL).content.decode()
    # Single-column stack (flex-col), images at container width (w-full), no grid.
    assert "flex-col" in body
    assert "w-full" in body
    assert "grid-cols" not in body


def test_gallery_orders_by_order_field(client):
    IllustrationFactory(title="Second", order=2, published=True)
    IllustrationFactory(title="First", order=1, published=True)
    body = client.get(GALLERY_URL).content.decode()
    assert body.index("First") < body.index("Second")


def test_gallery_serves_rendition_not_original(client):
    illo = IllustrationFactory(published=True)
    body = client.get(GALLERY_URL).content.decode()
    assert illo.gallery_image.url in body
    assert illo.image.url not in body


def test_gallery_renders_transparent_png_source(client):
    # An illustrator may upload an RGBA PNG; the JPEG rendition must not 500.
    png = SimpleUploadedFile("alpha.png", _png_rgba_bytes(), content_type="image/png")
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
    manual = SimpleUploadedFile("thumb.jpg", _jpeg_bytes(), content_type="image/jpeg")
    illo = IllustrationFactory(thumbnail=manual)
    assert illo.thumbnail_url == illo.thumbnail.url
    assert illo.thumbnail_url != illo.thumbnail_rendition.url


# --- helpers ---

def _jpeg_bytes():
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, "JPEG")
    return buf.getvalue()


def _png_rgba_bytes():
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGBA", (1600, 1200), (255, 0, 0, 128)).save(buf, "PNG")
    return buf.getvalue()
