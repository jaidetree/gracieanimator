from django.shortcuts import get_object_or_404, render

from portfolio.views import featured_projects

from .models import Page


def home(request):
    return render(request, "home.html", {"featured": featured_projects()})


def page_detail(request, slug):
    page = get_object_or_404(Page, slug=slug, published=True)
    return render(request, "pages/page_detail.html", {"page": page})
