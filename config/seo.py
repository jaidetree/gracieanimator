"""Site-wide SEO seams: the canonical-URL context processor and robots.txt.

The site renders live from more than one host (the custom domain plus the
herokuapp fallback). Both must keep serving, so we consolidate ranking signals
rather than redirect: every page advertises its canonical URL on a single host
(``settings.CANONICAL_HOST``), and robots.txt points crawlers at the sitemap on
that same host. Crawling stays open on every host on purpose — a ``rel=canonical``
only helps if the crawler can fetch the page to read it.
"""

from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse


def canonical_url(path):
    """The canonical absolute URL for a request path, on the canonical host.

    Always the canonical host, never the host that served the request: that is
    what tells a search engine the herokuapp copy and the custom-domain copy are
    the same page and should be scored as one. Built from ``request.path`` only,
    so query strings (tracking params, pagination noise) collapse to one URL.
    """
    return f"{settings.CANONICAL_SCHEME}://{settings.CANONICAL_HOST}{path}"


def canonical(request):
    """Expose ``canonical_url`` to every template (see ``base.html``'s <head>)."""
    return {"canonical_url": canonical_url(request.path)}


# Paths kept out of search results: the admin/editor surfaces, the storyboard
# password gate, and the gated storyboards themselves (a crawler only ever gets
# the login page). Crawling everything else stays allowed so canonical tags read.
ROBOTS_DISALLOW = ["/admin/", "/ckeditor5/", "/auth/", "/logout/", "/storyboards/"]


def robots_txt(request):
    """Serve robots.txt: allow the public site, hide the gated/admin paths, and
    point at the sitemap on the canonical host (same content on every host)."""
    lines = ["User-agent: *"]
    lines += [f"Disallow: {path}" for path in ROBOTS_DISALLOW]
    lines.append(f"Sitemap: {canonical_url(reverse('sitemap'))}")
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")
