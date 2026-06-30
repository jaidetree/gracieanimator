from django.contrib import admin

from common.admin.forms import CKEditorBodyForm

from .models import Page, PageFile


class PageAdminForm(CKEditorBodyForm):
    """Swaps the body's plain textarea for the CKEditor 5 widget (Slice 12).

    Inherits the themed ``body`` widget and its ``Media`` from
    ``CKEditorBodyForm``; supplies only the model and fieldset here.
    """

    class Meta:
        model = Page
        fields = ["title", "slug", "body", "published"]


class PageFileInline(admin.TabularInline):
    """Co-located file assets for a Page, uploaded inline.

    A plain inline (no ordering UX): the issue asks only to attach files.
    """

    model = PageFile
    extra = 1


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    form = PageAdminForm
    list_display = ("title", "slug", "published", "updated_at")
    list_editable = ("published",)
    list_filter = ("published",)
    search_fields = ("title", "body")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [PageFileInline]
