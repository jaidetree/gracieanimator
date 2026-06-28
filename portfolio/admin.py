from django.contrib import admin

from .models import Illustration, SketchbookSample


class ImageProjectAdmin(admin.ModelAdmin):
    """Shared admin config for single-image project types."""

    list_display = ("title", "slug", "order", "featured", "published", "updated_at")
    list_editable = ("order", "featured", "published")
    list_filter = ("published", "featured")
    search_fields = ("title",)
    ordering = ("order", "title")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Illustration)
class IllustrationAdmin(ImageProjectAdmin):
    pass


@admin.register(SketchbookSample)
class SketchbookSampleAdmin(ImageProjectAdmin):
    pass
