"""Site-wide SEO seams: the canonical-URL context processor and robots.txt.

The site renders live from more than one host (the custom domain plus the
herokuapp fallback). Both must keep serving, so we consolidate ranking signals
rather than redirect: every page advertises its canonical URL on a single host
(``settings.CANONICAL_HOST``), and robots.txt points crawlers at the sitemap on
that same host.

robots.txt is host-aware: the canonical host serves the real policy (open the
public site, hide the gated/admin paths), while every other host — herokuapp
fallback, preview, anything pointed at this app — gets a blanket Disallow so only
the custom domain is ever indexed.
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


def is_canonical_host(request):
    """Whether the request was served on the canonical host.

    ``get_host()`` may include a port; ``CANONICAL_HOST`` does not, so compare on
    the hostname only. The single source of truth for every host-aware indexing
    decision below, so robots.txt and the ``X-Robots-Tag`` header never disagree.
    """
    return request.get_host().split(":")[0] == settings.CANONICAL_HOST


def robots_txt(request):
    """Serve robots.txt.

    On the canonical host: allow the public site, hide the gated/admin paths, and
    point at the sitemap. On any other host (herokuapp fallback, preview): deny
    all crawling so only the custom domain gets indexed.
    """
    if not is_canonical_host(request):
        return HttpResponse("User-agent: *\nDisallow: /\n", content_type="text/plain")

    lines = ["User-agent: *"]
    lines += [f"Disallow: {path}" for path in ROBOTS_DISALLOW]
    lines.append(f"Sitemap: {canonical_url(reverse('sitemap'))}")
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def noindex_non_canonical_host(get_response):
    """Middleware: tag every response on a non-canonical host ``noindex``.

    robots.txt asks well-behaved crawlers not to fetch these hosts; this backstops
    the ones that crawl anyway (or have the page from before) by sending an
    ``X-Robots-Tag: noindex, nofollow`` header so the herokuapp/preview copies are
    dropped from the index. The canonical host is never tagged.
    """

    def middleware(request):
        response = get_response(request)
        if not is_canonical_host(request):
            response["X-Robots-Tag"] = "noindex, nofollow"
        return response

    return middleware
