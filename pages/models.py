from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Page(models.Model):
    """A standalone content page rendered live at /<slug>/.

    Body is plain text/HTML for now; a WYSIWYG editor arrives in a later slice.
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
        help_text="Page content. HTML is rendered as-is.",
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
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("page_detail", kwargs={"slug": self.slug})
