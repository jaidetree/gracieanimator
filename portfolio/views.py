from django.shortcuts import render

from .models import Illustration


def illustration_gallery(request):
    """Published illustrations as a single-column, full-width gallery."""
    illustrations = Illustration.objects.filter(published=True)
    return render(
        request,
        "portfolio/illustration_gallery.html",
        {"illustrations": illustrations, "page_title": "Illustrations"},
    )
