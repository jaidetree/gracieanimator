from django.shortcuts import render

from .models import Illustration, SketchbookSample


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
