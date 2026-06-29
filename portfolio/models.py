import os

from django.db import models
from django.utils.text import slugify
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFit

from richtext import sanitize_html

from . import oembed

# The site container is max-w-5xl (64rem / 1024px); gallery images render at that
# width, so the container-width rendition is capped there.
CONTAINER_WIDTH = 1024
# Bounding box for grid/thumbnail renditions (e.g. the homepage, Slice 11). The
# image is scaled to fit within this box with its aspect ratio intact and no
# crop; each grid surface frames it to its own aspect with CSS object-cover
# (equivalent to background-size: cover), so a single uncropped rendition serves
# the 5:4 homepage and 3:2 storyboard grids without the double-crop that a
# pre-cropped square would cause.
THUMBNAIL_SIZE = 400
# Width of comic page renditions on the two-column comics index. Sized to the
# on-screen cover/grid cell so the small rendition isn't upscaled into a blur;
# detail serves the full-resolution original instead.
COMIC_GRID_WIDTH = 600


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
    own media and supply ``_derived_thumbnail_url`` for the auto-thumbnail.
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
    # published before featured: nearly every piece is published, while only one
    # per type is featured, so the common toggle leads in forms and listings.
    published = models.BooleanField(
        default=True,
        help_text="Unpublished pieces are hidden from the public site.",
    )
    featured = models.BooleanField(
        default=False,
        help_text="Highlight one piece of this type on the homepage.",
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
        """The single seam every surface (homepage tile, section grids) asks for
        a piece's display thumbnail, so one piece renders one image everywhere.
        The manual-wins rule lives here once; each type supplies only how it
        serves a manual upload and how it derives one when none is set. None when
        nothing fits — the shared partial renders that as no DOM (a CSS color
        block downstream)."""
        if self.thumbnail:
            return self._manual_thumbnail_url()
        return self._derived_thumbnail_url()

    def _manual_thumbnail_url(self):
        """The manual upload as served on grids: the full image, unless a type
        serves a small rendition of it instead (Storyboard)."""
        return self.thumbnail.url

    def _derived_thumbnail_url(self):
        """Auto-derived thumbnail when no manual upload is set; None when the
        type has nothing to derive one from."""
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
    # Small rendition for grid surfaces (homepage), auto-derived from the image
    # so a blank thumbnail still has something to show. Scaled to fit, not
    # cropped: the grid's object-cover does the framing (see THUMBNAIL_SIZE).
    thumbnail_rendition = ImageSpecField(
        source="image",
        processors=[ResizeToFit(THUMBNAIL_SIZE, THUMBNAIL_SIZE)],
        format="JPEG",
        options={"quality": 80},
    )

    class Meta(Project.Meta):
        abstract = True

    def _derived_thumbnail_url(self):
        return self.thumbnail_rendition.url


class Illustration(ImageProject):
    """A single uploaded image, shown full-width in the illustrations gallery."""

    image = models.ImageField(upload_to="illustrations/")


class SketchbookSample(ImageProject):
    """A single uploaded image, shown full-width in the sketchbook gallery."""

    image = models.ImageField(upload_to="sketchbook_samples/")


class Comic(Project):
    """A multi-page comic. The media lives on an ordered collection of
    ``ComicPage`` rows; the comic itself carries only the shared Project fields.

    Page 1 is the cover and the comics index uses it as the linking thumbnail
    when no manual thumbnail is set.
    """

    @property
    def ordered_pages(self):
        """Pages in authored order (``ComicPage.Meta.ordering``)."""
        return self.pages.all()

    @property
    def cover_page(self):
        """The first page, used as the index cover; None when there are none."""
        return self.pages.first()

    def _derived_thumbnail_url(self):
        cover = self.cover_page
        return cover.grid_image.url if cover else None


class Storyboard(Project):
    """A storyboard piece: a rich body plus ordered embedded media.

    Media lives on three ordered child collections — ``StoryboardVideo``
    (Vimeo/YouTube), ``StoryboardDeck`` (Speakerdeck), and ``StoryboardPDF``
    (uploaded file). A storyboard needs something to show — at least one video
    *or* a manual thumbnail — enforced by the admin inline formset (the parent
    saves before its children, so it can't be a model rule). The thumbnail
    auto-derives from the first video's oembed poster when blank; a manual
    upload wins, and the absence of any poster leaves it to a CSS color block
    downstream.
    """

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="storyboards",
        help_text="Grouping label for the storyboards section.",
    )
    body = models.TextField(
        blank=True,
        help_text="Rich body, edited with the rich-text editor (Slice 12).",
    )

    # Small rendition of a *manual* thumbnail, for the index/category grids.
    # Only the manual upload can be rendered: the auto-derived thumbnail is an
    # external oembed poster URL (Vimeo/YouTube), not a local image file. Scaled
    # to fit, not cropped — the 3:2 grid's object-cover frames it.
    thumbnail_rendition = ImageSpecField(
        source="thumbnail",
        processors=[ResizeToFit(THUMBNAIL_SIZE, THUMBNAIL_SIZE)],
        format="JPEG",
        options={"quality": 80},
    )

    def save(self, *args, **kwargs):
        # Sanitize the WYSIWYG body here (not just in the admin form) so stored
        # HTML is safe regardless of entry point; Project.save handles the slug.
        self.body = sanitize_html(self.body)
        super().save(*args, **kwargs)

    def _manual_thumbnail_url(self):
        """The manual upload as its small rendition — a grid never needs the full
        image, and renditioning it makes a manual thumbnail render at the same
        size as a derived poster."""
        return self.thumbnail_rendition.url

    def _derived_thumbnail_url(self):
        """The first video's external (un-renditionable) oembed poster, or None
        when no video has one."""
        first_video = self.videos.first()
        if first_video and first_video.poster_url:
            return first_video.poster_url
        return None


class OEmbedMedia(models.Model):
    """Abstract base for a provider URL whose oembed result is cached on save.

    On save the URL is resolved through the oembed client (ADR-0002) once and
    the embed HTML and dimensions are cached on the row, so public rendering
    never touches the provider. Resolution is skipped when nothing needs it (an
    unchanged, already-resolved URL), so a no-op re-save makes no network call.
    A provider that can't be reached never blocks the save: the URL is kept with
    empty cache, and a later re-save retries.
    """

    url = models.URLField(max_length=500)
    embed_html = models.TextField(blank=True)
    embed_width = models.PositiveIntegerField(null=True, blank=True)
    embed_height = models.PositiveIntegerField(null=True, blank=True)
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the storyboard; lower numbers first.",
    )

    class Meta:
        abstract = True
        ordering = ["order", "id"]

    def __str__(self):
        return self.url

    def save(self, *args, **kwargs):
        if self._needs_oembed():
            self._resolve_oembed()
        super().save(*args, **kwargs)

    def _needs_oembed(self):
        """Resolve only when there's something to fetch: a URL that's unresolved
        (new row or a prior failure) or that has changed since the last save."""
        if not self.url:
            return False
        if not self.embed_html:
            return True
        if self.pk is None:
            return True
        previous = (
            type(self).objects.filter(pk=self.pk).values_list("url", flat=True).first()
        )
        return previous != self.url

    def _resolve_oembed(self):
        try:
            result = oembed.fetch(self.url)
        except oembed.OEmbedError:
            # Keep the URL but drop any cache: on a URL change the old embed now
            # describes a different (gone) URL, so a stale embed must not stick.
            # (We only get here when the cache is already empty or the URL
            # changed, so clearing is always safe.) A later re-save retries.
            self._clear_oembed()
            return
        self._apply_oembed(result)

    def _apply_oembed(self, result):
        self.embed_html = result.html
        self.embed_width = result.width
        self.embed_height = result.height

    def _clear_oembed(self):
        self.embed_html = ""
        self.embed_width = None
        self.embed_height = None


class StoryboardVideo(OEmbedMedia):
    """An embedded video (Vimeo/YouTube) on a Storyboard, with a cached poster.

    The poster is the storyboard's auto-thumbnail source (first video wins).
    """

    storyboard = models.ForeignKey(
        Storyboard, related_name="videos", on_delete=models.CASCADE
    )
    poster_url = models.URLField(max_length=500, blank=True)

    def _apply_oembed(self, result):
        super()._apply_oembed(result)
        self.poster_url = result.poster_url or ""

    def _clear_oembed(self):
        super()._clear_oembed()
        self.poster_url = ""


class StoryboardDeck(OEmbedMedia):
    """An embedded slide deck (Speakerdeck) on a Storyboard. No poster."""

    storyboard = models.ForeignKey(
        Storyboard, related_name="decks", on_delete=models.CASCADE
    )


class StoryboardPDF(models.Model):
    """An uploaded PDF (or other file) on a Storyboard, with a display name.

    ``FileField`` (not ``ImageField``) so non-image types are accepted, stored
    on the configured backend (R2 in deployed environments).
    """

    storyboard = models.ForeignKey(
        Storyboard, related_name="pdfs", on_delete=models.CASCADE
    )
    file = models.FileField(upload_to="storyboards/pdfs/")
    display_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Label shown for the download link. Defaults to the filename.",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the storyboard; lower numbers first.",
    )

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.label

    @property
    def label(self):
        """Display name, falling back to the uploaded file's basename."""
        return self.display_name or os.path.basename(self.file.name)


class ComicPage(models.Model):
    """One image within a Comic. Ordered by ``order`` then insertion id, so the
    admin inline's row order is the public render order.
    """

    comic = models.ForeignKey(Comic, related_name="pages", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="comics/")
    order = models.PositiveIntegerField(
        default=0,
        help_text="Page order within the comic; lower numbers appear first.",
    )

    # Small rendition for the two-column index (cover + pages beneath). Detail
    # serves the full-resolution original, so no large rendition is needed.
    grid_image = ImageSpecField(
        source="image",
        processors=[ResizeToFit(width=COMIC_GRID_WIDTH)],
        format="JPEG",
        options={"quality": 80},
    )

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.comic.title} — page {self.order}"
