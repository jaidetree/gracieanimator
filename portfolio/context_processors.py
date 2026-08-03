from core import url_names

PORTFOLIO_URL_NAMES = {
    url_names.HOME,
    url_names.ILLUSTRATION_GALLERY,
    url_names.SKETCHBOOK_SAMPLE_GALLERY,
    url_names.COMICS_INDEX,
    url_names.COMIC_DETAIL,
    url_names.COMIC_PAGE,
    url_names.STORYBOARD_GALLERY,
    url_names.STORYBOARD_CATEGORY,
    url_names.STORYBOARD_DETAIL,
}


def portfolio_nav(request):
    """Whether the current page belongs to the Portfolio nav section."""
    match = request.resolver_match
    is_active = match is not None and match.url_name in PORTFOLIO_URL_NAMES
    return {"portfolio_nav_active": is_active}
