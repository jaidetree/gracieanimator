"""The XML sitemap, pinned to the canonical host.

Django's sitemap framework derives the host from the request (no
``django.contrib.sites`` here), which would emit herokuapp URLs when the sitemap
is fetched on the herokuapp host. We override the host to ``CANONICAL_HOST`` so
every listed URL matches the ``rel=canonical`` the pages declare — one
consistent address per page, whichever host served the sitemap.

Storyboards are deliberately absent: they sit behind a password gate, so a
crawler only ever reaches the login page. Comics list one URL per comic (the
detail page), never the per-page pagination routes.
"""

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from pages.models import Page
from portfolio.models import Comic


class _CanonicalSite:
    """A stand-in for ``django.contrib.sites`` carrying only the canonical host,
    so ``Sitemap.get_urls`` builds absolute URLs there instead of on the request
    host."""

    domain = settings.CANONICAL_HOST
    name = settings.CANONICAL_HOST


class CanonicalSitemap(Sitemap):
    """Base sitemap that pins generated URLs to the canonical host + scheme."""

    protocol = settings.CANONICAL_SCHEME

    def get_urls(self, page=1, site=None, protocol=None):
        return super().get_urls(
            page=page, site=_CanonicalSite(), protocol=self.protocol
        )


class StaticViewSitemap(CanonicalSitemap):
    """The fixed top-level pages: home and the public section indexes."""

    def items(self):
        return [
            "home",
            "illustration_gallery",
            "sketchbook_sample_gallery",
            "comics_index",
        ]

    def location(self, item):
        return reverse(item)


class ComicSitemap(CanonicalSitemap):
    """Published comics, one entry each (the detail page, not its pages)."""

    def items(self):
        return Comic.objects.filter(published=True)

    def lastmod(self, comic):
        return comic.updated_at

    def location(self, comic):
        return reverse("comic_detail", kwargs={"slug": comic.slug})


class PageSitemap(CanonicalSitemap):
    """Published standalone pages (rendered at ``/<slug>/``)."""

    def items(self):
        return Page.objects.filter(published=True)

    def lastmod(self, page):
        return page.updated_at

    def location(self, page):
        return page.get_absolute_url()


sitemaps = {
    "static": StaticViewSitemap,
    "comics": ComicSitemap,
    "pages": PageSitemap,
}
