"""WYSIWYG rich-body sanitize pipeline (Slice 12).

Two acceptance criteria pull against each other: the stored body must be
*sanitized* (no scripts/handlers) yet *keep* the editor's inline image and media
embed so they render on the public page. The tests below assert survival of a
valid image and a valid embed — not merely that ``<script>`` is stripped — and
that an embed put in a Page body renders as an ``<iframe>`` on the public view.

The CKEditor upload view is exercised against the local filesystem storage; the
same code path writes to R2 in any real deploy (it targets ``STORAGES["default"]``),
which is not hit here.
"""

from io import BytesIO

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django_ckeditor_5.storage_utils import get_django_storage
from django_ckeditor_5.widgets import CKEditor5Widget
from PIL import Image

from pages.admin import PageAdminForm
from pages.models import Page
from pages.tests.factories import PageFactory
from richtext import sanitize_html

pytestmark = pytest.mark.django_db


def test_page_admin_form_uses_ckeditor_widget_for_body():
    assert isinstance(PageAdminForm().fields["body"].widget, CKEditor5Widget)


# Markup mirroring CKEditor 5's output: a wrapped inline image and a media embed
# with previewsInData (the provider iframe lives in the body).
IMAGE_HTML = (
    '<figure class="image"><img src="https://cdn.example/pic.png" alt="A"></figure>'
)
EMBED_HTML = (
    '<figure class="media"><div data-oembed-url="https://youtu.be/abc">'
    '<iframe src="https://www.youtube.com/embed/abc" allowfullscreen></iframe>'
    "</div></figure>"
)


# --- the sanitizer in isolation ------------------------------------------------


def test_sanitize_strips_scripts_and_event_handlers():
    dirty = '<script>alert(1)</script><p onclick="steal()">hi</p>'
    clean = sanitize_html(dirty)
    assert "<script" not in clean
    assert "onclick" not in clean
    assert "<p>hi</p>" in clean


def test_sanitize_drops_javascript_urls():
    clean = sanitize_html('<a href="javascript:alert(1)">x</a>')
    assert "javascript:" not in clean


def test_sanitize_keeps_inline_image():
    clean = sanitize_html(IMAGE_HTML)
    assert 'src="https://cdn.example/pic.png"' in clean
    assert 'class="image"' in clean


def test_sanitize_keeps_media_embed_iframe():
    clean = sanitize_html(EMBED_HTML)
    assert "<iframe" in clean
    assert "youtube.com/embed/abc" in clean
    assert "data-oembed-url" in clean


def test_sanitize_leaves_empty_body_empty():
    assert sanitize_html("") == ""


def test_sanitize_collapses_visually_empty_body():
    # CKEditor emits <p>&nbsp;</p> for a "blank" doc; collapse it so the public
    # {% if body %} stays false (no empty section / phantom "More" nav link).
    assert sanitize_html("<p>&nbsp;</p>") == ""
    assert sanitize_html("<p>  </p>") == ""


def test_sanitize_keeps_media_only_body():
    # A body that's only an image/embed (no prose) is still real content.
    assert sanitize_html(IMAGE_HTML) != ""


# --- the model save seam -------------------------------------------------------


def test_page_save_sanitizes_body_but_keeps_image_and_embed():
    page = Page.objects.create(
        title="Rich",
        body="<script>evil()</script>" + IMAGE_HTML + EMBED_HTML,
    )
    page.refresh_from_db()
    assert "<script" not in page.body
    assert "cdn.example/pic.png" in page.body  # image survived
    assert "youtube.com/embed/abc" in page.body  # embed survived


# --- public rendering ----------------------------------------------------------


def test_published_page_renders_embed_iframe(client):
    page = PageFactory(slug="embed-page", body=EMBED_HTML)
    html = client.get(f"/{page.slug}/").content.decode()
    assert '<iframe src="https://www.youtube.com/embed/abc"' in html


# --- inline image upload -> default storage ------------------------------------


def _png_upload():
    buf = BytesIO()
    Image.new("RGB", (4, 4), "blue").save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile("inline.png", buf.read(), content_type="image/png")


def test_inline_image_upload_persists_and_returns_url(client, settings, tmp_path):
    # Keep the write on the local filesystem (CI's R2 env would target the live
    # bucket — see LEARNINGS); the upload view writes to STORAGES["default"].
    settings.MEDIA_ROOT = tmp_path
    staff = User.objects.create_user("editor", password="pw", is_staff=True)
    client.force_login(staff)

    resp = client.post("/ckeditor5/image_upload/", {"upload": _png_upload()})

    assert resp.status_code == 200
    url = resp.json()["url"]
    assert url  # a usable URL back to the stored object
    # Assert through the same storage the view wrote to (order-independent: a
    # process-cached default_storage location wouldn't honour MEDIA_ROOT here).
    name = url.rsplit("/", 1)[-1]
    assert get_django_storage().exists(name)


def test_inline_image_upload_requires_staff(client):
    resp = client.post("/ckeditor5/image_upload/", {"upload": _png_upload()})
    assert resp.status_code == 403
