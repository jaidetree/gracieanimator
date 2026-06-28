from django.db import models
from django.utils.text import slugify
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill, ResizeToFit

# The site container is max-w-5xl (64rem / 1024px); gallery images render at that
# width, so the container-width rendition is capped there.
CONTAINER_WIDTH = 1024
# Square crop used for grid/thumbnail surfaces (e.g. the homepage, Slice 11).
THUMBNAIL_SIZE = 400


def thumbnail_upload_to(instance, filename):
    """Namespace manual thumbnails by concrete type, e.g. illustration/thumbnails/."""
    return f"{instance._meta.model_name}/thumbnails/{filename}"


class Category(models.Model):
    """A grouping label for Storyboards only (e.g. ``/storyboards/category/<slug>/``).

    Stands alone — no Storyboard consumer yet (a later slice). Slug is derived
    from the name when left blank.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        help_text="Auto-generated from the name; override for a custom URL.",
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Project(models.Model):
    """Abstract base for every portfolio piece (ADR-0003).

    Carries the fields common to all project types. Concrete subclasses add their
    own media and supply ``derived_thumbnail_url`` for the auto-thumbnail.
    """

    title = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=200,
        unique=True,
        blank=True,
        help_text="Auto-generated from the title; override for a custom URL.",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Manual display order; lower numbers appear first.",
    )
    featured = models.BooleanField(
        default=False,
        help_text="Highlight one piece of this type on the homepage.",
    )
    published = models.BooleanField(
        default=False,
        help_text="Unpublished pieces are hidden from the public site.",
    )
    thumbnail = models.ImageField(
        upload_to=thumbnail_upload_to,
        blank=True,
        help_text="Optional; auto-derived from the piece when left blank.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["order", "title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def _unique_slug(self):
        """A slug unique within this concrete type, appending -2, -3, … on clash."""
        base = slugify(self.title)
        slug = base
        siblings = type(self).objects.exclude(pk=self.pk)
        n = 2
        while siblings.filter(slug=slug).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    @property
    def thumbnail_url(self):
        """Manual thumbnail when set, else the type's auto-derived rendition."""
        if self.thumbnail:
            return self.thumbnail.url
        return self.derived_thumbnail_url

    @property
    def derived_thumbnail_url(self):
        """URL of the auto-derived thumbnail; None when nothing is available."""
        return None


class ImageProject(Project):
    """Abstract base for single-image project types (Illustration, Sketchbook
    Sample): structurally identical per ADR-0003 but distinct display groupings.

    Subclasses declare their own ``image`` field (so each gets its own
    ``upload_to`` namespace); the renditions and thumbnail fallback live here.
    ImageSpecFields are imagekit descriptors, not DB columns, so they add no
    per-subclass migration state.
    """

    # Container-width rendition for the single-column gallery (full image is
    # reserved for a detail view, which these types don't have).
    gallery_image = ImageSpecField(
        source="image",
        processors=[ResizeToFit(width=CONTAINER_WIDTH)],
        format="JPEG",
        options={"quality": 85},
    )
    # Small square rendition for grid surfaces (homepage), auto-derived from the
    # image so a blank thumbnail still has something to show.
    thumbnail_rendition = ImageSpecField(
        source="image",
        processors=[ResizeToFill(THUMBNAIL_SIZE, THUMBNAIL_SIZE)],
        format="JPEG",
        options={"quality": 80},
    )

    class Meta(Project.Meta):
        abstract = True

    @property
    def derived_thumbnail_url(self):
        return self.thumbnail_rendition.url


class Illustration(ImageProject):
    """A single uploaded image, shown full-width in the illustrations gallery."""

    image = models.ImageField(upload_to="illustrations/")


class SketchbookSample(ImageProject):
    """A single uploaded image, shown full-width in the sketchbook gallery."""

    image = models.ImageField(upload_to="sketchbook_samples/")
