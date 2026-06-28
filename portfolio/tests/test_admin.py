import io
from types import SimpleNamespace

import pytest
from django.contrib.admin.sites import site
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms.models import inlineformset_factory
from django.test import RequestFactory
from PIL import Image

from portfolio.admin import (
    ComicAdmin,
    ComicPageInline,
    IllustrationAdmin,
    SketchbookSampleAdmin,
)
from portfolio.models import Comic, ComicPage, Illustration, SketchbookSample
from portfolio.tests.factories import (
    ComicFactory,
    ComicPageFactory,
    IllustrationFactory,
    SketchbookSampleFactory,
)

# Concrete project types whose admin/model wiring this slice (#16) refined.
PROJECT_MODELS = [Illustration, SketchbookSample, Comic]
PROJECT_ADMINS = [IllustrationAdmin, SketchbookSampleAdmin, ComicAdmin]

# (admin class, model, factory) for the auto-increment-order behaviour (#16).
ORDERED_ADMINS = [
    (IllustrationAdmin, Illustration, IllustrationFactory),
    (SketchbookSampleAdmin, SketchbookSample, SketchbookSampleFactory),
    (ComicAdmin, Comic, ComicFactory),
]


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


# --- add form pre-fills the next order (#16, before saving) ---

@pytest.mark.django_db
@pytest.mark.parametrize("admin_cls,model,factory", ORDERED_ADMINS)
def test_add_form_prefills_next_order(admin_cls, model, factory):
    factory(order=5)
    request = RequestFactory().get("/add/")
    initial = admin_cls(model, site).get_changeform_initial_data(request)
    assert initial["order"] == 6


@pytest.mark.django_db
@pytest.mark.parametrize("admin_cls,model,factory", ORDERED_ADMINS)
def test_add_form_prefills_one_for_first_piece(admin_cls, model, factory):
    request = RequestFactory().get("/add/")
    initial = admin_cls(model, site).get_changeform_initial_data(request)
    assert initial["order"] == 1


@pytest.mark.django_db
@pytest.mark.parametrize("admin_cls,model,factory", ORDERED_ADMINS)
def test_add_form_order_from_url_wins(admin_cls, model, factory):
    factory(order=5)
    request = RequestFactory().get("/add/", {"order": "2"})
    initial = admin_cls(model, site).get_changeform_initial_data(request)
    assert initial["order"] == "2"


# --- auto-increment order on save (#16, server-side backstop) ---

@pytest.mark.django_db
@pytest.mark.parametrize("admin_cls,model,factory", ORDERED_ADMINS)
def test_new_piece_left_at_zero_lands_at_end(admin_cls, model, factory):
    # A new piece saved at the default order 0 takes max(order)+1 for its type.
    factory(order=5)
    obj = model(title="New")
    admin_cls(model, site).save_model(None, obj, None, change=False)
    assert obj.order == 6


@pytest.mark.django_db
@pytest.mark.parametrize("admin_cls,model,factory", ORDERED_ADMINS)
def test_first_piece_of_a_type_gets_order_one(admin_cls, model, factory):
    obj = model(title="First")
    admin_cls(model, site).save_model(None, obj, None, change=False)
    assert obj.order == 1


@pytest.mark.django_db
@pytest.mark.parametrize("admin_cls,model,factory", ORDERED_ADMINS)
def test_next_order_spans_unpublished_pieces(admin_cls, model, factory):
    # Maxed over all rows, so a new piece can't collide with a hidden one's order.
    factory(order=5, published=False)
    obj = model(title="New")
    admin_cls(model, site).save_model(None, obj, None, change=False)
    assert obj.order == 6


@pytest.mark.django_db
@pytest.mark.parametrize("admin_cls,model,factory", ORDERED_ADMINS)
def test_explicit_order_is_respected(admin_cls, model, factory):
    factory(order=5)
    obj = model(title="Pinned", order=2)
    admin_cls(model, site).save_model(None, obj, None, change=False)
    assert obj.order == 2


@pytest.mark.django_db
@pytest.mark.parametrize("admin_cls,model,factory", ORDERED_ADMINS)
def test_editing_existing_piece_does_not_renumber(admin_cls, model, factory):
    # An existing row legitimately at order 0 is left alone on edit.
    piece = factory(order=0)
    piece.title = "Edited"
    admin_cls(model, site).save_model(None, piece, None, change=True)
    assert piece.order == 0


# --- comic page inline auto-numbering (#16, bullet 1) ---

def _jpeg(name):
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, "JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


def _save_pages(comic, rows):
    """Drive ComicAdmin.save_formset over ``rows`` of {order, name} new pages.

    Builds the same bound inline formset the admin would and returns the comic's
    resulting page orders in render order.
    """
    formset_cls = inlineformset_factory(
        Comic, ComicPage, fields=("order", "image"), extra=0, can_delete=True
    )
    prefix = "pages"
    data = {
        f"{prefix}-TOTAL_FORMS": str(len(rows)),
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }
    files = {}
    for i, row in enumerate(rows):
        data[f"{prefix}-{i}-order"] = str(row["order"])
        files[f"{prefix}-{i}-image"] = _jpeg(f"{i}.jpg")
    formset = formset_cls(data, files, instance=comic, prefix=prefix)
    assert formset.is_valid(), formset.errors
    ComicAdmin(Comic, site).save_formset(
        None, SimpleNamespace(instance=comic), formset, change=False
    )
    return [p.order for p in comic.pages.all()]


def test_comic_page_inline_loads_order_script():
    assert "portfolio/comic_page_order.js" in ComicPageInline.Media.js


def test_comic_page_inline_shows_no_blank_row_by_default():
    # No always-present extra row: it would render order 0 (prefill can't touch
    # it without forcing an image-required error). Rows are added on demand.
    assert ComicPageInline.extra == 0


@pytest.mark.django_db
def test_new_pages_number_sequentially_from_one():
    comic = ComicFactory(order=0)
    orders = _save_pages(comic, [{"order": 0}, {"order": 0}, {"order": 0}])
    assert orders == [1, 2, 3]


@pytest.mark.django_db
def test_new_pages_continue_past_existing_pages():
    comic = ComicFactory(order=0)
    ComicPageFactory(comic=comic, order=5)
    orders = _save_pages(comic, [{"order": 0}, {"order": 0}])
    assert orders == [5, 6, 7]


@pytest.mark.django_db
def test_explicit_page_order_is_respected():
    comic = ComicFactory(order=0)
    # 9 can't coincide with sequential numbering, so this fails if it's renumbered.
    orders = _save_pages(comic, [{"order": 9}, {"order": 0}])
    # The pinned page keeps 9; the blank one is numbered from the existing max.
    assert sorted(orders) == [1, 9]
