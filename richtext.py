"""Sanitize WYSIWYG-authored HTML before it is stored (Slice 12).

Page and Storyboard bodies are edited with CKEditor 5 in the admin and rendered
with ``|safe`` on public pages, so the stored HTML must already be trustworthy.
The single guarantee lives on each model's ``save()`` (the same "resolve once on
save" seam as the oembed cache, ADR-0002): whatever reaches the database has been
run through :func:`sanitize_html`, regardless of how it got there.

The allowlist is deliberately wider than nh3's default because two acceptance
criteria pull against a default sanitizer: it must *keep* CKEditor's image
(``<figure class="image"><img></figure>``) and media-embed
(``<figure class="media">…<iframe></iframe>``) markup while still stripping
scripts and event handlers. Authors are trusted staff, so ``<iframe>`` is allowed
for provider embeds; URLs are restricted to http(s)/mailto/tel and inline CSS to a
handful of layout properties, so a pasted ``javascript:`` URL or ``expression()``
style is still dropped.
"""

import html
import re

import nh3

# Layout-only inline styles CKEditor emits for image sizing and alignment. Any
# other CSS property (and thus url()/expression payloads) is stripped.
_STYLE_PROPERTIES = {"width", "height", "text-align", "float", "aspect-ratio"}

# nh3's defaults already cover prose tags (p, headings, lists, figure, img, …);
# iframe is the one CKEditor needs that nh3 omits.
ALLOWED_TAGS = set(nh3.ALLOWED_TAGS) | {"iframe"}

# Merge onto nh3's per-tag defaults so standard attributes (a@href, img@alt, …)
# survive; add the ones CKEditor's image/embed wrappers depend on.
ALLOWED_ATTRIBUTES = {tag: set(attrs) for tag, attrs in nh3.ALLOWED_ATTRIBUTES.items()}
# nh3 manages a@rel itself (link_rel), so don't list it here — doing so raises.
ALLOWED_ATTRIBUTES.setdefault("a", set()).update({"href", "title", "target"})
ALLOWED_ATTRIBUTES.setdefault("img", set()).update(
    {"src", "alt", "width", "height", "srcset", "sizes", "style"}
)
ALLOWED_ATTRIBUTES["iframe"] = {
    "src",
    "width",
    "height",
    "allow",
    "allowfullscreen",
    "frameborder",
    "scrolling",
    "title",
    "style",
}
ALLOWED_ATTRIBUTES["figure"] = {"class", "style"}
ALLOWED_ATTRIBUTES["figcaption"] = {"class"}
# CKEditor's media embed wraps the iframe in <div class="… ck-media__wrapper"
# data-oembed-url="…">; keep both so the embed round-trips and renders.
ALLOWED_ATTRIBUTES["div"] = {"class", "data-oembed-url"}
ALLOWED_ATTRIBUTES["oembed"] = {"url"}
ALLOWED_ATTRIBUTES["td"] = {"colspan", "rowspan"}
ALLOWED_ATTRIBUTES["th"] = {"colspan", "rowspan"}
# CKEditor tags blocks/inlines with classes (alignment, "image", "media",
# "text-tiny", …); allow class on every tag rather than enumerate them.
ALLOWED_ATTRIBUTES["*"] = {"class"}

_URL_SCHEMES = {"http", "https", "mailto", "tel"}

# Tags that carry meaning even with no text (an embed/image is "content"); their
# presence keeps a body non-empty.
_NON_EMPTY_TAGS = re.compile(r"<(img|iframe|figure|video|audio)\b", re.IGNORECASE)
_TAGS = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"[\s ]+")  # incl. &nbsp; (U+00A0)


def _is_visually_empty(value):
    """True when ``value`` renders nothing — e.g. CKEditor's ``<p>&nbsp;</p>`` for
    a "blank" body. Media tags count as content even without text."""
    if _NON_EMPTY_TAGS.search(value):
        return False
    text = _TAGS.sub("", html.unescape(value))
    return not _WHITESPACE.sub("", text)


def sanitize_html(value):
    """Return ``value`` with everything outside the allowlist removed.

    A blank or visually-empty body collapses to ``""`` so the public templates'
    ``{% if body %}`` stays false (no empty ``#content`` section / phantom "More"
    nav link from a stray ``<p>&nbsp;</p>``).
    """
    if not value:
        return value
    cleaned = nh3.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=_URL_SCHEMES,
        filter_style_properties=_STYLE_PROPERTIES,
    )
    return "" if _is_visually_empty(cleaned) else cleaned
