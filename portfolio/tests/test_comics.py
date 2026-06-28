import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from portfolio.tests.factories import ComicFactory, ComicPageFactory, make_comic

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


# --- detail seam: full resolution, page navigation, bounds ---

def test_detail_serves_full_resolution_original(client):
    comic = make_comic(n_pages=2)
    cover = comic.cover_page
    body = client.get(f"/comics/{comic.slug}/").content.decode()
    assert cover.image.url in body


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
    assert f'class="comic__prev" href="/comics/{comic.slug}/"' in body


def test_middle_page_has_both_navigation_links(client):
    comic = make_comic(n_pages=3)
    body = client.get(f"/comics/{comic.slug}/page/2/").content.decode()
    assert "comic__prev" in body
    assert "comic__next" in body


def test_out_of_range_pages_404(client):
    comic = make_comic(n_pages=2)
    assert client.get(f"/comics/{comic.slug}/page/0/").status_code == 404
    assert client.get(f"/comics/{comic.slug}/page/3/").status_code == 404


def test_unpublished_comic_detail_404(client):
    comic = make_comic(n_pages=2, published=False)
    assert client.get(f"/comics/{comic.slug}/").status_code == 404


# --- helpers ---

def _jpeg_bytes():
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, "JPEG")
    return buf.getvalue()
