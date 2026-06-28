import pytest

from portfolio.admin import ComicAdmin, IllustrationAdmin, SketchbookSampleAdmin
from portfolio.models import Comic, Illustration, SketchbookSample

# Concrete project types whose admin/model wiring this slice (#16) refined.
PROJECT_MODELS = [Illustration, SketchbookSample, Comic]
PROJECT_ADMINS = [IllustrationAdmin, SketchbookSampleAdmin, ComicAdmin]


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
