import json

import pytest
from adminsortable2.admin import SortableAdminMixin, SortableInlineAdminMixin
from django.contrib.admin.sites import site
from django.test import RequestFactory
from django.urls import reverse

from portfolio.admin import (
    ComicAdmin,
    ComicPageInline,
    IllustrationAdmin,
    SketchbookSampleAdmin,
    StoryboardAdmin,
    StoryboardDeckInline,
    StoryboardPDFInline,
    StoryboardVideoInline,
)
from portfolio.models import Comic, Illustration, SketchbookSample
from portfolio.tests.factories import (
    ComicFactory,
    IllustrationFactory,
    SketchbookSampleFactory,
    StoryboardFactory,
    StoryboardVideoFactory,
)

# Concrete project types and their admins.
PROJECT_MODELS = [Illustration, SketchbookSample, Comic]
PROJECT_ADMINS = [IllustrationAdmin, SketchbookSampleAdmin, ComicAdmin]

# (admin class, model, factory) for order-assignment behaviour.
ORDERED_ADMINS = [
    (IllustrationAdmin, Illustration, IllustrationFactory),
    (SketchbookSampleAdmin, SketchbookSample, SketchbookSampleFactory),
    (ComicAdmin, Comic, ComicFactory),
]


def _instance(admin_cls, model):
    return admin_cls(model, site)


# --- published defaults to True (model seam) ---


@pytest.mark.parametrize("model", PROJECT_MODELS)
def test_published_defaults_to_true(model):
    # Nearly every piece is published, so a fresh instance is published by default.
    assert model().published is True


# --- featured sits below published (form + listing order) ---


@pytest.mark.parametrize("model", PROJECT_MODELS)
def test_model_orders_published_before_featured(model):
    # The admin change form has no explicit fields, so it follows _meta.fields.
    names = [f.name for f in model._meta.fields]
    assert names.index("published") < names.index("featured")


@pytest.mark.parametrize("admin_cls", PROJECT_ADMINS)
def test_list_display_orders_published_before_featured(admin_cls):
    cols = admin_cls.list_display
    assert cols.index("published") < cols.index("featured")


@pytest.mark.parametrize("admin_cls", PROJECT_ADMINS)
def test_list_editable_orders_published_before_featured(admin_cls):
    cols = admin_cls.list_editable
    assert cols.index("published") < cols.index("featured")


# --- drag-and-drop wiring (#19) ---


@pytest.mark.parametrize("admin_cls", PROJECT_ADMINS)
def test_project_changelists_are_sortable(admin_cls):
    assert issubclass(admin_cls, SortableAdminMixin)


def test_comic_page_inline_is_sortable():
    assert issubclass(ComicPageInline, SortableInlineAdminMixin)


@pytest.mark.django_db
@pytest.mark.parametrize("admin_cls,model,factory", ORDERED_ADMINS)
def test_changelist_shows_drag_handle_on_the_left(admin_cls, model, factory):
    # The drag handle is the leftmost column (issue: "handle graphic on the
    # left") and the bare order column never renders.
    request = RequestFactory().get("/")
    columns = _instance(admin_cls, model).get_list_display(request)
    assert columns[0] == "_reorder_"
    assert "order" not in columns


@pytest.mark.parametrize("admin_cls", PROJECT_ADMINS)
def test_order_is_not_inline_editable(admin_cls):
    # order is reordered by drag, never by an inline changelist input — it isn't a
    # displayed column, so listing it in list_editable would have nowhere to render.
    assert "order" not in admin_cls.list_editable


# --- the order number stays typeable on the change form, not the add form (#19) ---


@pytest.mark.django_db
@pytest.mark.parametrize("admin_cls,model,factory", ORDERED_ADMINS)
def test_change_form_keeps_editable_order(admin_cls, model, factory):
    piece = factory()
    request = RequestFactory().get("/change/")
    fields = _instance(admin_cls, model).get_fields(request, obj=piece)
    assert "order" in fields


@pytest.mark.parametrize("admin_cls,model,factory", ORDERED_ADMINS)
def test_add_form_omits_order(admin_cls, model, factory):
    # New pieces are auto-numbered to the end on save, so the add form hides order.
    request = RequestFactory().get("/add/")
    fields = _instance(admin_cls, model).get_fields(request, obj=None)
    assert "order" not in fields


# --- new pieces auto-number to the end on add (#19, via sortable2 save_model) ---


@pytest.mark.django_db
@pytest.mark.parametrize("admin_cls,model,factory", ORDERED_ADMINS)
def test_new_piece_lands_at_end(admin_cls, model, factory):
    factory(order=5)
    obj = model(title="New")
    _instance(admin_cls, model).save_model(None, obj, None, change=False)
    assert obj.order == 6


@pytest.mark.django_db
@pytest.mark.parametrize("admin_cls,model,factory", ORDERED_ADMINS)
def test_first_piece_of_a_type_gets_order_one(admin_cls, model, factory):
    obj = model(title="First")
    _instance(admin_cls, model).save_model(None, obj, None, change=False)
    assert obj.order == 1


@pytest.mark.django_db
@pytest.mark.parametrize("admin_cls,model,factory", ORDERED_ADMINS)
def test_editing_existing_piece_does_not_renumber(admin_cls, model, factory):
    # On edit, save_model leaves the (possibly hand-typed) order untouched.
    piece = factory(order=3)
    piece.title = "Edited"
    _instance(admin_cls, model).save_model(None, piece, None, change=True)
    assert piece.order == 3


# --- the bulk reorder endpoint persists a drag in one request (#19) ---


@pytest.mark.django_db
def test_reorder_endpoint_persists_new_order(admin_client):
    first = IllustrationFactory(order=1)
    second = IllustrationFactory(order=2)
    url = reverse("admin:portfolio_illustration_sortable_update")

    response = admin_client.post(
        url,
        data=json.dumps({"updatedItems": [[first.pk, 2], [second.pk, 1]]}),
        content_type="application/json",
    )

    assert response.status_code == 200
    first.refresh_from_db()
    second.refresh_from_db()
    assert (first.order, second.order) == (2, 1)


@pytest.mark.django_db
def test_reorder_cleans_up_gaps_across_whole_collection(admin_client):
    # A gappy collection (left by deletes / add-at-end). sortable2 alone would
    # only reindex the moved span; our override renumbers the whole collection.
    a = IllustrationFactory(order=1)
    b = IllustrationFactory(order=5)
    c = IllustrationFactory(order=9)
    url = reverse("admin:portfolio_illustration_sortable_update")

    # Drag c to the front (the JS sends only the moved item's new span order).
    response = admin_client.post(
        url,
        data=json.dumps({"updatedItems": [[c.pk, 0]]}),
        content_type="application/json",
    )

    assert response.status_code == 200
    orders = dict(Illustration.objects.values_list("pk", "order"))
    assert sorted(orders.values()) == [1, 2, 3]  # no gaps anywhere
    assert orders[c.pk] == 1  # c is first
    assert orders[a.pk] < orders[b.pk]  # untouched relative order preserved


@pytest.mark.django_db
def test_reorder_endpoint_rejects_get(admin_client):
    url = reverse("admin:portfolio_illustration_sortable_update")
    assert admin_client.get(url).status_code == 405


# --- the comic inline keeps its no-blank-row behaviour (#16) ---


def test_comic_page_inline_shows_no_blank_row_by_default():
    assert ComicPageInline.extra == 0


# --- storyboard admin: sortable changelist + three sortable inlines (#10) ---


def test_storyboard_changelist_is_sortable():
    assert issubclass(StoryboardAdmin, SortableAdminMixin)


@pytest.mark.parametrize(
    "inline", [StoryboardVideoInline, StoryboardDeckInline, StoryboardPDFInline]
)
def test_storyboard_inlines_are_sortable(inline):
    assert issubclass(inline, SortableInlineAdminMixin)
    assert inline.extra == 0


def test_storyboard_registers_all_three_media_inlines():
    assert StoryboardAdmin.inlines == [
        StoryboardVideoInline,
        StoryboardDeckInline,
        StoryboardPDFInline,
    ]


@pytest.mark.parametrize(
    "inline,verbose,plural",
    [
        (StoryboardVideoInline, "video", "videos"),
        (StoryboardDeckInline, "deck", "decks"),
        (StoryboardPDFInline, "PDF", "PDFs"),
    ],
)
def test_storyboard_inlines_drop_the_model_name_prefix(inline, verbose, plural):
    # The inline labels read "video"/"deck"/"PDF", not "Storyboard video" etc.
    assert inline.verbose_name == verbose
    assert inline.verbose_name_plural == plural


@pytest.mark.django_db
def test_storyboard_add_form_renders_three_inlines(admin_client):
    # Proves the three sortable inlines coexist on one change form (the library
    # only had a single-inline precedent before this slice) and that the
    # "Storyboard" prefix is gone from their "Add another …" labels.
    response = admin_client.get(reverse("admin:portfolio_storyboard_add"))
    assert response.status_code == 200
    body = response.content.decode()
    for prefix in ("videos", "decks", "pdfs"):
        assert f"{prefix}-TOTAL_FORMS" in body
    assert "Storyboard video" not in body
    assert "Storyboard deck" not in body


@pytest.mark.django_db
def test_storyboard_change_form_renders_with_saved_media(admin_client):
    sb = StoryboardFactory()
    StoryboardVideoFactory(storyboard=sb, url="https://vimeo.com/1")
    url = reverse("admin:portfolio_storyboard_change", args=[sb.pk])
    response = admin_client.get(url)
    assert response.status_code == 200
    assert "https://vimeo.com/1" in response.content.decode()


def _storyboard_add_post(category, *, videos):
    """Minimal admin add-form POST: main fields + the three inline mgmt forms."""
    data = {
        "title": "Posted Storyboard",
        "slug": "",
        "category": str(category.pk),
        "body": "<p>body</p>",
        "published": "on",
        "videos-TOTAL_FORMS": str(len(videos)),
        "videos-INITIAL_FORMS": "0",
        "videos-MIN_NUM_FORMS": "0",
        "videos-MAX_NUM_FORMS": "1000",
        "decks-TOTAL_FORMS": "0",
        "decks-INITIAL_FORMS": "0",
        "decks-MIN_NUM_FORMS": "0",
        "decks-MAX_NUM_FORMS": "1000",
        "pdfs-TOTAL_FORMS": "0",
        "pdfs-INITIAL_FORMS": "0",
        "pdfs-MIN_NUM_FORMS": "0",
        "pdfs-MAX_NUM_FORMS": "1000",
    }
    for i, url in enumerate(videos):
        data[f"videos-{i}-url"] = url
        data[f"videos-{i}-order"] = str(i)
    return data


@pytest.mark.django_db
def test_storyboard_saves_through_admin_and_caches_embed(admin_client):
    # Full add path: the 3-inline form saves and the video's save() resolves
    # oembed (stubbed in conftest) and caches the embed on the row.
    from portfolio.models import Storyboard, StoryboardVideo
    from portfolio.tests.factories import CategoryFactory

    category = CategoryFactory()
    response = admin_client.post(
        reverse("admin:portfolio_storyboard_add"),
        _storyboard_add_post(category, videos=["https://vimeo.com/555"]),
    )
    assert response.status_code == 302  # redirect on success
    sb = Storyboard.objects.get(title="Posted Storyboard")
    video = StoryboardVideo.objects.get(storyboard=sb)
    assert video.url == "https://vimeo.com/555"
    assert video.embed_html  # cached by save() via the stubbed oembed client


@pytest.mark.django_db
def test_storyboard_admin_rejects_save_with_no_video_and_no_thumbnail(admin_client):
    from portfolio.models import Storyboard
    from portfolio.tests.factories import CategoryFactory

    category = CategoryFactory()
    response = admin_client.post(
        reverse("admin:portfolio_storyboard_add"),
        _storyboard_add_post(category, videos=[]),
    )
    # Form re-renders (200, not a 302 redirect) with the validation error.
    assert response.status_code == 200
    assert "video or a thumbnail" in response.content.decode().lower()
    assert not Storyboard.objects.filter(title="Posted Storyboard").exists()


@pytest.mark.django_db
def test_storyboard_admin_accepts_thumbnail_without_video(admin_client):
    # The migrated case: a thumbnail and no video saves cleanly. Proves the
    # uploaded thumbnail is visible on self.instance during the inline formset's
    # clean (admin binds it to the parent before building the inlines).
    from io import BytesIO

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    from portfolio.models import Storyboard
    from portfolio.tests.factories import CategoryFactory

    category = CategoryFactory()
    data = _storyboard_add_post(category, videos=[])
    # A real image: ImageField runs Pillow validation on the admin POST path.
    buffer = BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, "PNG")
    thumbnail = SimpleUploadedFile("t.png", buffer.getvalue(), content_type="image/png")
    response = admin_client.post(
        reverse("admin:portfolio_storyboard_add"),
        {**data, "thumbnail": thumbnail},
    )
    assert response.status_code == 302
    assert Storyboard.objects.get(title="Posted Storyboard").thumbnail
