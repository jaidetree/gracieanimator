from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from richtext import sanitize_html


class Page(models.Model):
    """A standalone content page rendered live at /<slug>/.

    Body is WYSIWYG-authored HTML (CKEditor 5 in the admin, Slice 12), sanitized
    on save so the public template can render it with ``|safe``.
    """

    title = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=200,
        unique=True,
        blank=True,
        help_text="Auto-generated from the title; override for a custom URL.",
    )
    body = models.TextField(
        blank=True,
        help_text="Page content, edited with the rich-text editor.",
    )
    published = models.BooleanField(
        default=False,
        help_text="Unpublished pages are hidden from the site and its navigation.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        # Sanitize here (not just in the admin form) so the stored HTML is safe
        # no matter how the row was written.
        self.body = sanitize_html(self.body)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("page_detail", kwargs={"slug": self.slug})


class PageFile(models.Model):
    """An asset co-located with a Page (image, PDF, or any other file type).

    These are uploads an editor wants kept alongside a page — they may or may not
    be referenced in the body. ``FileField`` (not ``ImageField``) so non-image
    types like PDFs are accepted.
    """

    page = models.ForeignKey(Page, related_name="files", on_delete=models.CASCADE)
    file = models.FileField(upload_to="pages/files/")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.file.name
