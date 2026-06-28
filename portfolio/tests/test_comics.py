import re

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from portfolio.tests.factories import ComicFactory, ComicPageFactory, make_comic
from portfolio.views import adjacent_comics

pytestmark = pytest.mark.django_db

INDEX_URL = "/comics/"


# --- model seam: ordering, cover, thumbnail fallback ---

def test_pages_render_in_authored_order():
    comic = ComicFactory()
    ComicPageFactory(comic=comic, order=2)
    ComicPageFactory(comic=comic, order=0)
    ComicPageFactory(comic=comic, order=1)
    assert [p.order for p in comic.ordered_pages] == [0, 1, 2]


def test_cover_page_is_first_page():
    comic = make_comic(n_pages=3)
    assert comic.cover_page == comic.ordered_pages[0]


def test_slug_auto_generated_from_title():
    comic = ComicFactory(title="Dumpling Eternal", slug="")
    assert comic.slug == "dumpling-eternal"


def test_thumbnail_defaults_to_first_page_when_blank():
    comic = make_comic(n_pages=2)
    assert not comic.thumbnail
    assert comic.thumbnail_url == comic.cover_page.grid_image.url


def test_manual_thumbnail_wins():
    manual = SimpleUploadedFile("thumb.jpg", _jpeg_bytes(), content_type="image/jpeg")
    comic = make_comic(n_pages=2, thumbnail=manual)
    assert comic.thumbnail_url == comic.thumbnail.url
    assert comic.thumbnail_url != comic.cover_page.grid_image.url


def test_derived_thumbnail_none_without_pages():
    comic = ComicFactory()
    assert comic.derived_thumbnail_url is None


# --- index seam: two-column grid, links, renditions, publishing ---

def test_index_is_two_column_desktop_grid(client):
    make_comic(n_pages=2)
    body = client.get(INDEX_URL).content.decode()
    assert "md:grid-cols-2" in body


def test_index_cover_links_into_comic(client):
    comic = make_comic(n_pages=2, title="Cover Linker")
    body = client.get(INDEX_URL).content.decode()
    assert f'href="/comics/{comic.slug}/"' in body


def test_index_lays_remaining_pages_beneath_linking_to_page_routes(client):
    comic = make_comic(n_pages=3, title="Beneath")
    body = client.get(INDEX_URL).content.decode()
    # Pages 2 and 3 link to their page routes; the cover (page 1) does not.
    assert f'href="/comics/{comic.slug}/page/2/"' in body
    assert f'href="/comics/{comic.slug}/page/3/"' in body
    assert f'href="/comics/{comic.slug}/page/1/"' not in body


def test_index_uses_small_rendition_not_original(client):
    comic = make_comic(n_pages=2)
    page = comic.ordered_pages[1]
    body = client.get(INDEX_URL).content.decode()
    assert page.grid_image.url in body
    assert page.image.url not in body


def test_index_shows_only_published_comics(client):
    shown = make_comic(n_pages=1, title="Visible Comic", published=True)
    hidden = make_comic(n_pages=1, title="Hidden Comic", published=False)
    body = client.get(INDEX_URL).content.decode()
    assert shown.title in body
    assert hidden.title not in body


# --- detail seam: page grid, selection, full resolution, navigation, bounds ---

def test_detail_serves_full_resolution_original(client):
    comic = make_comic(n_pages=2)
    cover = comic.cover_page
    body = client.get(f"/comics/{comic.slug}/").content.decode()
    assert cover.image.url in body


def test_detail_shows_every_page_in_an_aspect_respecting_grid(client):
    comic = make_comic(n_pages=3)
    pages = comic.ordered_pages
    body = client.get(f"/comics/{comic.slug}/").content.decode()
    assert "comic__pages" in body and "grid" in body
    # Unselected pages render their width-constrained, aspect-respecting rendition.
    assert pages[1].grid_image.url in body
    assert pages[2].grid_image.url in body
    assert "h-auto" in body


def test_detail_renders_no_raw_template_comment(client):
    # Multi-line {# #} comments aren't stripped by Django and leak as text.
    comic = make_comic(n_pages=2)
    body = client.get(f"/comics/{comic.slug}/").content.decode()
    assert "Thumbnail strip" not in body


def test_selected_page_is_full_opacity_others_dimmed_with_hover_transition(client):
    comic = make_comic(n_pages=3)
    body = client.get(f"/comics/{comic.slug}/page/2/").content.decode()
    assert "comic__page--selected" in body
    assert "opacity-100" in body  # selected page
    assert "opacity-50" in body  # dimmed pages
    # Dimmed pages lift to full opacity on hover, transitioning over 300ms.
    assert "hover:opacity-100" in body
    assert "transition-opacity" in body
    assert "duration-300" in body


def test_first_page_has_next_but_no_previous(client):
    comic = make_comic(n_pages=3)
    body = client.get(f"/comics/{comic.slug}/").content.decode()
    assert f'href="/comics/{comic.slug}/page/2/"' in body
    assert "comic__prev" not in body


def test_last_page_has_previous_but_no_next(client):
    comic = make_comic(n_pages=3)
    body = client.get(f"/comics/{comic.slug}/page/3/").content.decode()
    assert f'href="/comics/{comic.slug}/page/2/"' in body
    assert "comic__next" not in body


def test_previous_from_page_two_points_to_bare_detail_url(client):
    comic = make_comic(n_pages=3)
    body = client.get(f"/comics/{comic.slug}/page/2/").content.decode()
    # The prev chevron links to page 1's canonical (bare) URL.
    match = re.search(r'class="comic__prev[^"]*"[^>]*href="([^"]+)"', body)
    assert match and match.group(1) == f"/comics/{comic.slug}/"


def test_middle_page_has_both_navigation_links(client):
    comic = make_comic(n_pages=3)
    body = client.get(f"/comics/{comic.slug}/page/2/").content.decode()
    assert "comic__prev" in body
    assert "comic__next" in body


def test_nav_chevrons_are_centered_circles_with_hover_transition(client):
    comic = make_comic(n_pages=3)
    body = client.get(f"/comics/{comic.slug}/page/2/").content.decode()
    prev = re.search(r'<a class="comic__prev[^"]*"', body).group(0)
    # 48x48, vertically centered over the image, transitions, rounded with a
    # 10% black circle on mobile that clears on desktop. Chevron is an SVG.
    assert "w-12" in prev and "h-12" in prev
    assert "top-0" in prev and "bottom-0" in prev and "my-auto" in prev
    assert "rounded-full" in prev
    assert "bg-black/10" in prev and "lg:bg-transparent" in prev
    assert "transition" in prev
    assert "<svg" in body


def test_out_of_range_pages_404(client):
    comic = make_comic(n_pages=2)
    assert client.get(f"/comics/{comic.slug}/page/0/").status_code == 404
    assert client.get(f"/comics/{comic.slug}/page/3/").status_code == 404


def test_unpublished_comic_detail_404(client):
    comic = make_comic(n_pages=2, published=False)
    assert client.get(f"/comics/{comic.slug}/").status_code == 404


# --- sibling (prev/next comic) navigation ---

# adjacent_comics is pure list logic (index + modular indexing), so it's
# exercised with plain sentinels — no DB or ORM needed.

def test_adjacent_comics_returns_neighbours_in_sort_order():
    assert adjacent_comics(["a", "b", "c"], "b") == ("a", "c")


def test_adjacent_comics_wraps_around_the_ends():
    # First item's previous is the last; last item's next is the first.
    assert adjacent_comics(["a", "b", "c"], "a") == ("c", "b")
    assert adjacent_comics(["a", "b", "c"], "c") == ("b", "a")


def test_adjacent_comics_returns_none_for_a_lone_comic():
    assert adjacent_comics(["only"], "only") == (None, None)


def test_detail_renders_prev_next_comic_bar_with_cover_thumbnails(client):
    first = make_comic(n_pages=2, order=0, title="First Comic")
    middle = make_comic(n_pages=2, order=1, title="Middle Comic")
    last = make_comic(n_pages=2, order=2, title="Last Comic")
    body = client.get(f"/comics/{middle.slug}/").content.decode()
    assert "comic__siblings" in body
    # Distinct sort-order neighbours, each linked by its cover thumbnail.
    assert f'href="/comics/{first.slug}/"' in body
    assert f'href="/comics/{last.slug}/"' in body
    assert first.cover_page.grid_image.url in body
    assert last.cover_page.grid_image.url in body
    assert "prev:" in body and "next:" in body


def test_sibling_bar_omitted_for_a_lone_comic(client):
    only = make_comic(n_pages=2)
    body = client.get(f"/comics/{only.slug}/").content.decode()
    assert "comic__siblings" not in body


def test_sibling_bar_ignores_unpublished_comics(client):
    shown = make_comic(n_pages=1, order=0, title="Shown Comic")
    make_comic(n_pages=1, order=1, title="Draft Comic", published=False)
    body = client.get(f"/comics/{shown.slug}/").content.decode()
    # Only one published comic, so no sibling bar despite the draft existing.
    assert "comic__siblings" not in body


# --- helpers ---

def _jpeg_bytes():
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, "JPEG")
    return buf.getvalue()
