import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from pages.models import Page, PageFile
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


def test_page_accepts_non_image_file_attachment():
    # The whole point of FileField over ImageField: PDFs/other types attach.
    page = PageFactory()
    pdf = SimpleUploadedFile(
        "brief.pdf", b"%PDF-1.4 fake", content_type="application/pdf"
    )
    attachment = PageFile.objects.create(page=page, file=pdf)
    assert page.files.get() == attachment
    assert attachment.file.name.endswith(".pdf")


def test_page_files_cascade_on_page_delete():
    page = PageFactory()
    PageFile.objects.create(page=page, file=SimpleUploadedFile("a.txt", b"hi"))
    page.delete()
    assert PageFile.objects.count() == 0


def test_page_file_str_is_filename():
    page = PageFactory()
    attachment = PageFile.objects.create(
        page=page, file=SimpleUploadedFile("notes.txt", b"x")
    )
    assert "notes" in str(attachment)


def test_branded_404_template(client, settings):
    # Custom 404 template only renders with DEBUG off.
    settings.DEBUG = False
    client.raise_request_exception = False
    resp = client.get("/nope-not-here/")
    assert resp.status_code == 404
    assert "try a little harder" in resp.content.decode()
