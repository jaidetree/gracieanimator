"""Model-save-seam tests for Storyboard authoring + media (Slice 8).

The oembed boundary is mocked everywhere (autouse ``stub_oembed`` in conftest;
individual tests override ``portfolio.oembed.fetch`` to exercise the caching,
unreachable, and re-save paths). Validation is driven through the real admin
inline formset, since the "video or thumbnail" rule can't live on the model.
"""

import os
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms.models import inlineformset_factory
from PIL import Image

from portfolio import oembed
from portfolio.admin import RequireVideoOrThumbnailFormSet
from portfolio.models import Storyboard, StoryboardVideo
from portfolio.tests.factories import (
    StoryboardDeckFactory,
    StoryboardFactory,
    StoryboardPDFFactory,
    StoryboardVideoFactory,
)

pytestmark = pytest.mark.django_db


def _oembed(**overrides):
    base = {
        "provider": "vimeo",
        "html": '<iframe src="x"></iframe>',
        "width": 1280,
        "height": 720,
        "poster_url": "https://i.vimeocdn.com/video/abc.jpg",
    }
    base.update(overrides)
    return oembed.OEmbed(**base)


# --- structure ---


def test_storyboard_is_a_project_with_category_and_body():
    sb = StoryboardFactory(body="<p>hello</p>")
    assert isinstance(sb, Storyboard)
    assert sb.category is not None
    assert sb.body == "<p>hello</p>"
    assert sb.slug  # Project.save derives the slug


def test_category_is_required():
    field = Storyboard._meta.get_field("category")
    assert field.null is False


def test_deleting_an_in_use_category_is_protected():
    from django.db.models import ProtectedError

    sb = StoryboardFactory()
    with pytest.raises(ProtectedError):
        sb.category.delete()


# --- AC2: oembed fetched once on save, embed cached on the row ---


def test_video_save_caches_embed_and_poster(monkeypatch):
    monkeypatch.setattr(
        oembed,
        "fetch",
        lambda url: _oembed(html="<iframe>cached</iframe>", width=640, height=360),
    )
    video = StoryboardVideoFactory(url="https://vimeo.com/12345")
    video.refresh_from_db()
    assert video.embed_html == "<iframe>cached</iframe>"
    assert (video.embed_width, video.embed_height) == (640, 360)
    assert video.poster_url == "https://i.vimeocdn.com/video/abc.jpg"


def test_deck_save_caches_embed_without_poster(monkeypatch):
    monkeypatch.setattr(
        oembed,
        "fetch",
        lambda url: _oembed(
            provider="speakerdeck", html="<iframe>deck</iframe>", poster_url=None
        ),
    )
    deck = StoryboardDeckFactory(url="https://speakerdeck.com/u/t")
    assert deck.embed_html == "<iframe>deck</iframe>"
    assert not hasattr(deck, "poster_url")


def test_oembed_fetched_once_unchanged_resave_skips_fetch(monkeypatch):
    calls = []

    def _fetch(url):
        calls.append(url)
        return _oembed()

    monkeypatch.setattr(oembed, "fetch", _fetch)
    video = StoryboardVideoFactory(url="https://vimeo.com/99")
    assert calls == ["https://vimeo.com/99"]

    # A no-op re-save (order touched, URL unchanged) must not re-fetch.
    video.order = 5
    video.save()
    assert calls == ["https://vimeo.com/99"]


def test_changing_url_refetches(monkeypatch):
    calls = []

    def _fetch(url):
        calls.append(url)
        return _oembed()

    monkeypatch.setattr(oembed, "fetch", _fetch)
    video = StoryboardVideoFactory(url="https://vimeo.com/1")
    video.url = "https://vimeo.com/2"
    video.save()
    assert calls == ["https://vimeo.com/1", "https://vimeo.com/2"]


# --- AC4: unreachable provider keeps the URL, doesn't block, allows re-save ---


def test_unreachable_provider_keeps_url_and_resave_recovers(monkeypatch):
    def _down(url):
        raise oembed.OEmbedError("provider unreachable")

    monkeypatch.setattr(oembed, "fetch", _down)
    video = StoryboardVideoFactory(url="https://vimeo.com/77")
    # Save succeeded: row persisted with the URL, empty cache.
    video.refresh_from_db()
    assert video.url == "https://vimeo.com/77"
    assert video.embed_html == ""

    # Provider recovers; a re-save (URL unchanged) retries and now caches.
    monkeypatch.setattr(
        oembed, "fetch", lambda url: _oembed(html="<iframe>up</iframe>")
    )
    video.save()
    video.refresh_from_db()
    assert video.embed_html == "<iframe>up</iframe>"


def test_changing_url_to_unreachable_clears_stale_embed(monkeypatch):
    # A resolved video re-pointed at a now-unreachable URL must not keep the old
    # embed/poster (they describe the gone URL); a later re-save then recovers.
    monkeypatch.setattr(oembed, "fetch", lambda url: _oembed(html="<iframe>A</iframe>"))
    video = StoryboardVideoFactory(url="https://vimeo.com/a")
    assert video.embed_html == "<iframe>A</iframe>"

    def _down(url):
        raise oembed.OEmbedError("down")

    monkeypatch.setattr(oembed, "fetch", _down)
    video.url = "https://vimeo.com/b"
    video.save()
    video.refresh_from_db()
    assert video.embed_html == ""  # no stale A embed against URL b
    assert video.poster_url == ""

    monkeypatch.setattr(oembed, "fetch", lambda url: _oembed(html="<iframe>B</iframe>"))
    video.save()
    video.refresh_from_db()
    assert video.embed_html == "<iframe>B</iframe>"


# --- AC5: thumbnail derives from first video poster; manual wins; None fallback ---


def test_thumbnail_derives_from_first_video_poster(monkeypatch):
    monkeypatch.setattr(
        oembed, "fetch", lambda url: _oembed(poster_url="https://poster/first.jpg")
    )
    sb = StoryboardFactory()
    StoryboardVideoFactory(storyboard=sb, order=0, url="https://vimeo.com/a")
    assert sb.thumbnail_url == "https://poster/first.jpg"


def test_first_video_in_order_wins(monkeypatch):
    sb = StoryboardFactory()
    monkeypatch.setattr(
        oembed, "fetch", lambda url: _oembed(poster_url="https://poster/second.jpg")
    )
    StoryboardVideoFactory(storyboard=sb, order=2, url="https://vimeo.com/b")
    monkeypatch.setattr(
        oembed, "fetch", lambda url: _oembed(poster_url="https://poster/first.jpg")
    )
    StoryboardVideoFactory(storyboard=sb, order=1, url="https://vimeo.com/a")
    assert sb.thumbnail_url == "https://poster/first.jpg"


def test_no_poster_yields_no_thumbnail(monkeypatch):
    monkeypatch.setattr(oembed, "fetch", lambda url: _oembed(poster_url=None))
    sb = StoryboardFactory()
    StoryboardVideoFactory(storyboard=sb, url="https://vimeo.com/c")
    assert sb.thumbnail_url is None


def test_no_videos_yields_no_thumbnail():
    sb = StoryboardFactory()
    assert sb.thumbnail_url is None


def test_manual_thumbnail_wins_over_video_poster(monkeypatch):
    monkeypatch.setattr(
        oembed, "fetch", lambda url: _oembed(poster_url="https://poster/auto.jpg")
    )
    buf = BytesIO()
    Image.new("RGB", (40, 40), "red").save(buf, "JPEG")
    image = SimpleUploadedFile("manual.jpg", buf.getvalue(), content_type="image/jpeg")
    sb = StoryboardFactory(thumbnail=image)
    StoryboardVideoFactory(storyboard=sb, url="https://vimeo.com/d")
    # The seam serves the small rendition of the manual upload, never the full
    # image and never the video poster.
    assert sb.thumbnail_url == sb.thumbnail_rendition.url
    assert "auto.jpg" not in sb.thumbnail_url
    assert "auto.jpg" not in sb.thumbnail_url


# --- AC6: PDF stores an uploaded file + display name ---


def test_pdf_stores_file_and_display_name():
    pdf = StoryboardPDFFactory(display_name="Project Brief")
    pdf.refresh_from_db()
    assert pdf.display_name == "Project Brief"
    assert pdf.label == "Project Brief"
    assert pdf.file.read() == b"%PDF-1.4 test"


def test_pdf_label_defaults_to_filename_when_display_name_blank():
    pdf = StoryboardPDFFactory(display_name="")
    assert pdf.label == os.path.basename(pdf.file.name)
    assert str(pdf) == pdf.label


# --- validation: a storyboard needs a video OR a thumbnail (real formset) ---

_THUMBNAIL = SimpleUploadedFile("thumb.png", b"img-bytes", content_type="image/png")


def _video_formset(n_videos, *, thumbnail=False):
    """Build the bound video inline formset the change form submits, with the
    admin's ``RequireVideoOrThumbnailFormSet`` clean rule wired in. ``extra=0``
    mirrors the inline (no always-present blank row), so ``n_videos`` filled rows
    is how the form expresses "this many videos". ``thumbnail`` seeds the parent
    instance's thumbnail (the rule reads ``self.instance.thumbnail``)."""
    sb = StoryboardFactory(thumbnail=_THUMBNAIL if thumbnail else "")
    formset_cls = inlineformset_factory(
        Storyboard,
        StoryboardVideo,
        formset=RequireVideoOrThumbnailFormSet,
        fields=("order", "url"),
        extra=0,
    )
    prefix = "videos"
    data = {
        f"{prefix}-TOTAL_FORMS": str(n_videos),
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }
    for i in range(n_videos):
        data[f"{prefix}-{i}-url"] = f"https://vimeo.com/{i}"
        data[f"{prefix}-{i}-order"] = str(i)
    # data passed by keyword: sortable2's CustomInlineFormSet.__init__ takes
    # default_order_* as its leading positional args, so a positional `data`
    # would be swallowed and the formset would come back unbound.
    return formset_cls(data=data, instance=sb, prefix=prefix)


def test_formset_invalid_with_no_video_and_no_thumbnail():
    formset = _video_formset(0, thumbnail=False)
    assert not formset.is_valid()
    assert "video or a thumbnail" in str(formset.non_form_errors()).lower()


def test_formset_valid_with_one_video_and_no_thumbnail():
    formset = _video_formset(1, thumbnail=False)
    assert formset.is_valid(), formset.errors or formset.non_form_errors()


def test_formset_valid_with_thumbnail_and_no_video():
    # The migrated case: a storyboard with only a thumbnail, no video.
    formset = _video_formset(0, thumbnail=True)
    assert formset.is_valid(), formset.errors or formset.non_form_errors()


def test_formset_invalid_when_last_video_deleted_and_no_thumbnail():
    # Editing: the one video is marked for deletion and there's no thumbnail, so
    # nothing is left to show — the rule fires.
    sb = StoryboardFactory()
    video = StoryboardVideoFactory(storyboard=sb, url="https://vimeo.com/x")
    formset_cls = inlineformset_factory(
        Storyboard,
        StoryboardVideo,
        formset=RequireVideoOrThumbnailFormSet,
        fields=("order", "url"),
        extra=0,
        can_delete=True,
    )
    data = {
        "videos-TOTAL_FORMS": "1",
        "videos-INITIAL_FORMS": "1",
        "videos-MIN_NUM_FORMS": "0",
        "videos-MAX_NUM_FORMS": "1000",
        "videos-0-id": str(video.pk),
        "videos-0-url": video.url,
        "videos-0-order": str(video.order),
        "videos-0-DELETE": "on",
    }
    formset = formset_cls(data=data, instance=sb, prefix="videos")
    assert not formset.is_valid()
    assert "video or a thumbnail" in str(formset.non_form_errors()).lower()


# --- WYSIWYG body sanitize seam (Slice 12) ------------------------------------


def test_storyboard_save_sanitizes_body_but_keeps_image_and_embed():
    """Storyboard.save runs the body through the sanitizer (same guarantee as
    Page), stripping scripts while keeping the editor's image and media embed."""
    sb = StoryboardFactory(
        body=(
            "<script>evil()</script>"
            '<figure class="image"><img src="https://cdn.example/b.png" alt="A"></figure>'
            '<figure class="media"><div data-oembed-url="https://youtu.be/z">'
            '<iframe src="https://www.youtube.com/embed/z"></iframe></div></figure>'
        )
    )
    sb.refresh_from_db()
    assert "<script" not in sb.body
    assert "cdn.example/b.png" in sb.body
    assert "youtube.com/embed/z" in sb.body
