"""SketchbookSample-specific behaviour.

The gallery layout, ordering, rendition, and published-filtering guarantees are
shared with Illustration and live in ``test_galleries.py``. Slug
generation/uniqueness lives on the shared base and is exercised by the
Illustration suite; here we only confirm the chain resolves for this type and
cover its thumbnail fallback.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from portfolio.tests.factories import SketchbookSampleFactory, jpeg_bytes

pytestmark = pytest.mark.django_db


# --- inheritance from the Project base (model seam) ---


def test_slug_auto_generated_from_title():
    sample = SketchbookSampleFactory(title="Morning Studies", slug="")
    assert sample.slug == "morning-studies"


# --- thumbnail fallback (model seam) ---


def test_thumbnail_auto_derives_from_image_when_blank():
    sample = SketchbookSampleFactory()
    assert not sample.thumbnail
    assert sample.thumbnail_url == sample.thumbnail_rendition.url


def test_manual_thumbnail_wins():
    manual = SimpleUploadedFile("thumb.jpg", jpeg_bytes(), content_type="image/jpeg")
    sample = SketchbookSampleFactory(thumbnail=manual)
    assert sample.thumbnail_url == sample.thumbnail.url
    assert sample.thumbnail_url != sample.thumbnail_rendition.url
