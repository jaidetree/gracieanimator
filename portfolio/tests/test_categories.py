import pytest

from portfolio.models import Category

pytestmark = pytest.mark.django_db


def test_slug_derived_from_name():
    category = Category.objects.create(name="Music Videos")
    assert category.slug == "music-videos"


def test_explicit_slug_is_not_overwritten():
    category = Category.objects.create(name="Music Videos", slug="custom")
    assert category.slug == "custom"


def test_str_is_the_name():
    assert str(Category(name="Commercials")) == "Commercials"


def test_categories_order_by_name():
    Category.objects.create(name="Shorts")
    Category.objects.create(name="Ads")
    assert [c.name for c in Category.objects.all()] == ["Ads", "Shorts"]
