from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from core import url_names
from core.seo import robots_txt
from core.sitemaps import sitemaps
from pages import views as page_views
from portfolio import storyboard_gate
from portfolio import views as portfolio_views

urlpatterns = [
    path("admin/", admin.site.urls),
    # SEO endpoints. Both live above the <slug:slug>/ catch-all, though neither
    # could collide with it: the slug converter excludes dots and these carry no
    # trailing slash. The sitemap is named "sitemap" so seo.robots_txt can
    # reverse it onto the canonical host.
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    # CKEditor 5 inline-image upload endpoint (Slice 12). Multi-segment, so it
    # never collides with the trailing <slug:slug>/ catch-all below.
    path("ckeditor5/", include("django_ckeditor_5.urls")),
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
    # Storyboard password gate (Slice 9): /auth/ unlocks the session, /logout/
    # re-locks it. Both are top-level per the spec; registered before the
    # catch-all slug route, which only matches what these don't.
    path("auth/", storyboard_gate.storyboards_login, name=url_names.STORYBOARD_AUTH),
    path(
        "logout/",
        storyboard_gate.storyboards_logout,
        name=url_names.STORYBOARD_LOGOUT,
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
