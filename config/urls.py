from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from pages import views as page_views
from portfolio import views as portfolio_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", page_views.home, name="home"),
    path("illustrations/", portfolio_views.illustration_gallery, name="illustration_gallery"),
    path(
        "sketchbook-samples/",
        portfolio_views.sketchbook_sample_gallery,
        name="sketchbook_sample_gallery",
    ),
    path("comics/", portfolio_views.comics_index, name="comics_index"),
    path("comics/<slug:slug>/", portfolio_views.comic_detail, name="comic_detail"),
    path(
        "comics/<slug:slug>/page/<int:page>/",
        portfolio_views.comic_detail,
        name="comic_page",
    ),
    # Catch-all top-level slug -> a published Page. Keep last.
    path("<slug:slug>/", page_views.page_detail, name="page_detail"),
]

# Serve uploaded media from the local filesystem during development. In
# production media lives on R2 (Slice 3) and is served by the storage backend.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
