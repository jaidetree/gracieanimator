"""SEO seams: canonical tag, robots.txt, and the canonical-host sitemap.

The point of the whole feature is that signals consolidate onto one host no
matter which host served the request, so the host-independence assertions (a
herokuapp-host request still advertising a gracieanimator.art canonical) are the
load-bearing ones.
"""

import pytest
from django.urls import reverse

from pages.tests.factories import PageFactory
from portfolio.tests.factories import ComicFactory

# A non-canonical host the site also answers on; ALLOWED_HOSTS lets the test
# client present it so we can prove the canonical signal ignores the serving host.
ALT_HOST = "gracieanimator-staging.herokuapp.com"


@pytest.fixture(autouse=True)
def canonical_settings(settings):
    """Pin the canonical host (independent of any deploy default) and let the
    client present the fallback host alongside the default ``testserver``."""
    settings.CANONICAL_HOST = "gracieanimator.art"
    settings.CANONICAL_SCHEME = "https"
    settings.ALLOWED_HOSTS = ["testserver", ALT_HOST]


@pytest.mark.django_db
class TestCanonicalTag:
    def test_home_declares_canonical_on_canonical_host(self, client):
        html = client.get("/").content.decode()
        assert (
            '<link rel="canonical" href="https://gracieanimator.art/">' in html
        )

    def test_canonical_uses_canonical_host_even_when_served_elsewhere(self, client):
        """A page served on the herokuapp fallback still points at the custom
        domain — this is what merges the two copies for search engines."""
        html = client.get("/", HTTP_HOST=ALT_HOST).content.decode()
        assert 'href="https://gracieanimator.art/"' in html
        assert ALT_HOST not in html.split("<body")[0]  # not in <head>

    def test_canonical_reflects_the_request_path(self, client):
        PageFactory(slug="about")
        html = client.get("/about/").content.decode()
        assert 'href="https://gracieanimator.art/about/"' in html


class TestRobotsTxt:
    def test_serves_plain_text(self, client):
        resp = client.get("/robots.txt")
        assert resp.status_code == 200
        assert resp["Content-Type"].startswith("text/plain")

    def test_disallows_admin_and_gated_paths(self, client):
        body = client.get("/robots.txt").content.decode()
        for path in ("/admin/", "/ckeditor5/", "/auth/", "/storyboards/"):
            assert f"Disallow: {path}" in body

    def test_advertises_sitemap_on_canonical_host(self, client):
        """Even fetched on the fallback host, robots points at the canonical
        sitemap, so crawlers index the custom domain's URLs."""
        body = client.get("/robots.txt", HTTP_HOST=ALT_HOST).content.decode()
        assert "Sitemap: https://gracieanimator.art/sitemap.xml" in body


@pytest.mark.django_db
class TestSitemap:
    def test_lists_published_comics_and_pages_on_canonical_host(self, client):
        ComicFactory(slug="my-comic", published=True)
        PageFactory(slug="about", published=True)
        xml = client.get("/sitemap.xml", HTTP_HOST=ALT_HOST).content.decode()

        assert "https://gracieanimator.art/comics/my-comic/" in xml
        assert "https://gracieanimator.art/about/" in xml
        # Host-pinned: never the serving host.
        assert ALT_HOST not in xml

    def test_includes_static_section_indexes(self, client):
        xml = client.get("/sitemap.xml").content.decode()
        for name in ("comics_index", "illustration_gallery", "sketchbook_sample_gallery"):
            assert f"https://gracieanimator.art{reverse(name)}" in xml

    def test_excludes_unpublished_and_gated_content(self, client):
        ComicFactory(slug="draft", published=False)
        xml = client.get("/sitemap.xml").content.decode()
        assert "draft" not in xml
        # Storyboards are password-gated, so they never belong in the sitemap.
        assert "/storyboards/" not in xml
