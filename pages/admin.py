from django.contrib import admin

from .models import Page, PageFile


class PageFileInline(admin.TabularInline):
    """Co-located file assets for a Page, uploaded inline.

    A plain inline (no ordering UX): the issue asks only to attach files.
    """

    model = PageFile
    extra = 1


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "published", "updated_at")
    list_editable = ("published",)
    list_filter = ("published",)
    search_fields = ("title", "body")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [PageFileInline]
