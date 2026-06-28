from django.http import Http404
from django.shortcuts import get_object_or_404, render

from .models import Comic, Illustration, SketchbookSample


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


def comics_index(request):
    """Published comics as a two-column desktop grid: each cover links into the
    comic, with the remaining pages laid out beneath."""
    comics = Comic.objects.filter(published=True).prefetch_related("pages")
    return render(
        request,
        "portfolio/comics_index.html",
        {"comics": comics, "page_title": "Comics"},
    )


def comic_detail(request, slug, page=1):
    """A single comic page (1-based) with no-JS previous/next navigation.

    ``/comics/<slug>/`` is page 1 (the cover); ``/comics/<slug>/page/<n>/``
    addresses page n. Out-of-range pages 404. Page 1's canonical URL is the bare
    detail URL, so the previous link from page 2 points there.
    """
    comic = get_object_or_404(Comic, slug=slug, published=True)
    pages = list(comic.ordered_pages)
    if not 1 <= page <= len(pages):
        raise Http404("No such comic page.")
    return render(
        request,
        "portfolio/comic_detail.html",
        {
            "comic": comic,
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
