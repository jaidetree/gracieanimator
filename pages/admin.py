from django import forms
from django.contrib import admin
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import Page, PageFile


class PageAdminForm(forms.ModelForm):
    """Swaps the body's plain textarea for the CKEditor 5 widget (Slice 12).

    The widget lives on the admin form, not the model, so the field stays a
    plain ``TextField`` (no migration) and the editor is an admin-only concern.
    ``body`` is declared explicitly (not via ``Meta.widgets``) so it carries the
    widget while the admin still supplies the rest of the fieldset itself.
    """

    body = forms.CharField(
        widget=CKEditor5Widget(config_name="default"), required=False
    )

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
