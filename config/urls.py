from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from config import url_names
from pages import views as page_views
from portfolio import views as portfolio_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", page_views.home, name=url_names.HOME),
    path(
        "illustrations/",
        portfolio_views.illustration_gallery,
        name=url_names.ILLUSTRATION_GALLERY,
    ),
    path(
        "sketchbook-samples/",
        portfolio_views.sketchbook_sample_gallery,
        name=url_names.SKETCHBOOK_SAMPLE_GALLERY,
    ),
    path("comics/", portfolio_views.comics_index, name=url_names.COMICS_INDEX),
    path(
        "comics/<slug:slug>/",
        portfolio_views.comic_detail,
        name=url_names.COMIC_DETAIL,
    ),
    path(
        "comics/<slug:slug>/page/<int:page>/",
        portfolio_views.comic_detail,
        name=url_names.COMIC_PAGE,
    ),
    path(
        "storyboards/",
        portfolio_views.storyboards_index,
        name=url_names.STORYBOARD_GALLERY,
    ),
    # The literal "category/" segment makes this two-segment route distinct from
    # the one-segment detail route below, so their relative order is irrelevant.
    path(
        "storyboards/category/<slug:slug>/",
        portfolio_views.storyboard_category,
        name=url_names.STORYBOARD_CATEGORY,
    ),
    path(
        "storyboards/<slug:slug>/",
        portfolio_views.storyboard_detail,
        name=url_names.STORYBOARD_DETAIL,
    ),
    # Catch-all top-level slug -> a published Page. Keep last.
    path("<slug:slug>/", page_views.page_detail, name=url_names.PAGE_DETAIL),
]

# Serve uploaded media from the local filesystem during development. In
# production media lives on R2 (Slice 3) and is served by the storage backend.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
