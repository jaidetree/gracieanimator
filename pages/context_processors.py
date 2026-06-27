from .models import Page


def nav_pages(request):
    """Published pages, surfaced in the site nav on every page."""
    return {"nav_pages": Page.objects.filter(published=True)}
