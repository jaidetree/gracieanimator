import pytest
from django.urls import reverse

from pages.models import Page
from pages.tests.factories import PageFactory

pytestmark = pytest.mark.django_db


def test_slug_auto_generated_from_title():
    page = Page.objects.create(title="About Me", published=True)
    assert page.slug == "about-me"


def test_explicit_slug_is_not_overwritten():
    page = Page.objects.create(title="About Me", slug="custom", published=True)
    assert page.slug == "custom"


def test_published_page_renders_at_slug(client):
    page = PageFactory(title="About", slug="about", body="<p>Hello world</p>")
    resp = client.get(f"/{page.slug}/")
    assert resp.status_code == 200
    assert "Hello world" in resp.content.decode()


def test_unpublished_page_404s(client):
    page = PageFactory(slug="secret", published=False)
    resp = client.get(f"/{page.slug}/")
    assert resp.status_code == 404


def test_published_page_appears_in_nav(client):
    PageFactory(title="Contact", slug="contact", published=True)
    body = client.get("/").content.decode()
    assert "Contact" in body
    assert reverse("page_detail", kwargs={"slug": "contact"}) in body


def test_unpublished_page_absent_from_nav(client):
    PageFactory(title="Draft", slug="draft", published=False)
    assert "Draft" not in client.get("/").content.decode()


def test_branded_404_template(client, settings):
    # Custom 404 template only renders with DEBUG off.
    settings.DEBUG = False
    client.raise_request_exception = False
    resp = client.get("/nope-not-here/")
    assert resp.status_code == 404
    assert "try a little harder" in resp.content.decode()
