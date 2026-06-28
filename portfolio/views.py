from functools import wraps

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme

from config import url_names

from .models import Category, Comic, Illustration, SketchbookSample, Storyboard

# Homepage grid: one featured piece per type, in display order. Each entry is
# (model, label, section_url); reverse_lazy resolves the section URL at
# import-safe time so the URL itself lives in the tuple, not a name to reverse.
# Route names come from config.url_names, so a bad name fails at import.
FEATURED_TYPES = [
    (Storyboard, "Storyboards", reverse_lazy(url_names.STORYBOARD_GALLERY)),
    (Illustration, "Illustrations", reverse_lazy(url_names.ILLUSTRATION_GALLERY)),
    (
        SketchbookSample,
        "Sketchbook Samples",
        reverse_lazy(url_names.SKETCHBOOK_SAMPLE_GALLERY),
    ),
    (Comic, "Comics", reverse_lazy(url_names.COMICS_INDEX)),
]


def featured_projects():
    """One featured, published piece per type for the homepage grid.

    For each type the lowest-``order`` featured+published piece wins
    (``Meta.ordering``), so several featured pieces resolve deterministically to
    one. A type with no eligible piece simply contributes nothing — the grid
    degrades gracefully. Each entry is self-contained: type label, thumbnail
    URL, and the section href.
    """
    selected = []
    for model, label, url in FEATURED_TYPES:
        piece = model.objects.filter(published=True, featured=True).first()
        if piece is not None:
            selected.append(
                {
                    "label": label,
                    "thumbnail_url": piece.thumbnail_url,
                    "url": url,
                }
            )
    return selected


def _image_gallery(request, model, page_title):
    """Published single-image pieces as a single-column, full-width gallery."""
    pieces = model.objects.filter(published=True)
    return render(
        request,
        "portfolio/image_gallery.html",
        {"pieces": pieces, "page_title": page_title},
    )


def illustration_gallery(request):
    return _image_gallery(request, Illustration, "Illustrations")


def sketchbook_sample_gallery(request):
    return _image_gallery(request, SketchbookSample, "Sketchbook Samples")


# Storyboards sit behind a single shared password (Slice 9). A correct POST to
# /auth/ sets this session flag, which unlocks every storyboard page for the
# browser session; the views below require it via @storyboards_required.
SESSION_AUTH_KEY = "storyboards_auth"


def storyboards_required(view):
    """Redirect to the storyboard login form unless the session is unlocked.

    The flag is browser-session scoped (``SESSION_EXPIRE_AT_BROWSER_CLOSE``), so
    one unlock covers every storyboard page until the browser closes or /logout/.
    The originally requested path rides along as ``next`` so login returns there.
    """

    @wraps(view)
    def guarded(request, *args, **kwargs):
        if request.session.get(SESSION_AUTH_KEY):
            return view(request, *args, **kwargs)
        login_url = reverse(url_names.STORYBOARD_AUTH)
        return redirect(f"{login_url}?next={request.path}")

    return guarded


def storyboards_login(request):
    """The password gate: GET shows the form, a correct POST unlocks the session.

    The shared password is read from settings; an unset (empty) password never
    unlocks, so a misconfigured deploy fails closed rather than open. On success
    the session flag is set and the visitor is sent to a safe ``next`` (their
    original destination) or the storyboards index.
    """
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = reverse(url_names.STORYBOARD_GALLERY)

    error = None
    if request.method == "POST":
        password = settings.STORYBOARDS_PASSWORD
        if password and request.POST.get("password") == password:
            request.session[SESSION_AUTH_KEY] = True
            return redirect(next_url)
        error = "Incorrect password."

    return render(
        request,
        "portfolio/storyboards_login.html",
        {"next": next_url, "error": error, "page_title": "Storyboards"},
    )


def storyboards_logout(request):
    """Clear the session flag (re-locking the storyboards) and return to login."""
    request.session.pop(SESSION_AUTH_KEY, None)
    return redirect(reverse(url_names.STORYBOARD_AUTH))


def _published_storyboards():
    """Published storyboards with their media prefetched for public rendering."""
    return Storyboard.objects.filter(published=True).prefetch_related(
        "videos", "decks", "pdfs"
    )


@storyboards_required
def storyboards_index(request):
    """Every category that has at least one published storyboard, each with its
    storyboards in a grid beneath the category heading. Empty categories are
    omitted so the index never shows a bare heading with nothing under it."""
    storyboards = _published_storyboards().select_related("category")
    groups = {}
    for storyboard in storyboards:
        groups.setdefault(storyboard.category, []).append(storyboard)
    # Category.Meta.ordering is by name; honour it for the section order.
    categories = sorted(groups, key=lambda c: c.name.lower())
    sections = [{"category": c, "storyboards": groups[c]} for c in categories]
    return render(
        request,
        "portfolio/storyboards_index.html",
        {"sections": sections, "page_title": "Storyboards"},
    )


@storyboards_required
def storyboard_category(request, slug):
    """A single category's published storyboards in one grid."""
    category = get_object_or_404(Category, slug=slug)
    storyboards = _published_storyboards().filter(category=category)
    return render(
        request,
        "portfolio/storyboard_category.html",
        {
            "category": category,
            "storyboards": storyboards,
            "page_title": category.name,
        },
    )


@storyboards_required
def storyboard_detail(request, slug):
    """One storyboard: its videos, decks, downloadable PDFs, and body, with a
    section-navigation sidebar. All embeds render from the cache populated on
    save (ADR-0002), so this view never calls the oembed provider."""
    storyboard = get_object_or_404(
        _published_storyboards().select_related("category"), slug=slug
    )
    return render(
        request,
        "portfolio/storyboard_detail.html",
        {
            "storyboard": storyboard,
            "videos": list(storyboard.videos.all()),
            "decks": list(storyboard.decks.all()),
            "pdfs": list(storyboard.pdfs.all()),
            "page_title": storyboard.title,
        },
    )


def comics_index(request):
    """Published comics as a two-column desktop grid: each cover links into the
    comic, with the remaining pages laid out beneath."""
    comics = Comic.objects.filter(published=True).prefetch_related("pages")
    return render(
        request,
        "portfolio/comics_index.html",
        {"comics": comics, "page_title": "Comics"},
    )


def adjacent_comics(comics, current):
    """The previous and next comic in sort order, without wrapping.

    ``comics`` is the ordered list of comics to navigate. The first comic has no
    previous and the last has no next (each returned as ``None``), so a reader
    can tell when they've reached an end rather than looping silently.
    """
    idx = comics.index(current)
    prev = comics[idx - 1] if idx > 0 else None
    next_ = comics[idx + 1] if idx < len(comics) - 1 else None
    return prev, next_


def comic_detail(request, slug, page=1):
    """A large view of the selected page above an aspect-respecting thumbnail
    strip of every page, one selected (1-based).

    The large image is the selected page at full resolution; the thumbnails let a
    visitor jump to any page and see where they are (selected at full opacity,
    the rest dimmed). No-JS previous/next links and the per-page routes also
    drive selection. ``/comics/<slug>/`` selects page 1 (the cover);
    ``/comics/<slug>/page/<n>/`` selects page n. Out-of-range pages 404. Page 1's
    canonical URL is the bare detail URL, so the previous link from page 2 points
    there. A bar at the foot links the previous/next comic in sort order (by
    cover thumbnail); the first and last comics omit the missing direction.
    """
    comic = get_object_or_404(Comic, slug=slug, published=True)
    pages = list(comic.ordered_pages)
    if not 1 <= page <= len(pages):
        raise Http404("No such comic page.")
    published_comics = list(Comic.objects.filter(published=True))
    prev_comic, next_comic = adjacent_comics(published_comics, comic)
    return render(
        request,
        "portfolio/comic_detail.html",
        {
            "comic": comic,
            "pages": pages,
            "prev_comic": prev_comic,
            "next_comic": next_comic,
            "page": pages[page - 1],
            "page_number": page,
            "page_count": len(pages),
            "has_previous": page > 1,
            "has_next": page < len(pages),
            "previous_number": page - 1,
            "next_number": page + 1,
            "page_title": comic.title,
        },
    )
