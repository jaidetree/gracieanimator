from adminsortable2.admin import (
    CustomInlineFormSet,
    SortableAdminMixin,
    SortableTabularInline,
)
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import (
    Category,
    Comic,
    ComicPage,
    Illustration,
    SketchbookSample,
    Storyboard,
    StoryboardDeck,
    StoryboardPDF,
    StoryboardVideo,
)
from .ordering import renumber


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Storyboard grouping labels; slug prepopulated from the name."""

    list_display = ("name", "slug")
    search_fields = ("name",)
    ordering = ("name",)
    prepopulated_fields = {"slug": ("name",)}


class SortableProjectAdmin(SortableAdminMixin, admin.ModelAdmin):
    """Drag-to-reorder changelist for a project type.

    django-admin-sortable2 inserts a drag handle (``_reorder_``) as the leftmost
    column and strips ``order`` from the change form. ``order`` is left out of
    ``list_display`` so the handle lands on the left as the issue asks (keeping
    ``order`` there would only shift the handle inward). ``get_fields`` re-adds
    ``order`` on the change form so an editor can still type a number by hand
    when editing an existing piece; new pieces are auto-numbered to the end on
    add (sortable2's ``save_model``), so the add form omits ``order``.

    ``order`` is deliberately *not* in ``list_editable`` (it isn't a displayed
    column, so an inline input would have nowhere to render);
    ``published``/``featured`` stay inline-editable.
    """

    list_display = ("title", "slug", "published", "featured", "updated_at")
    list_editable = ("published", "featured")
    list_filter = ("published", "featured")
    search_fields = ("title",)
    ordering = ("order", "title")
    prepopulated_fields = {"slug": ("title",)}

    class Media:
        # Narrow sortable2's 50px-wide drag-handle column.
        css = {"all": ("portfolio/sortable_admin.css",)}

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if obj is not None and "order" not in fields:
            fields.append("order")
        return fields

    def _update_order(self, updated_items, extra_model_filters):
        """Apply the dragged span, then renumber the whole collection 1..N.

        sortable2's drag only reindexes the rows between the drag's start and end
        position, so gaps elsewhere (left by deletes or the add-at-end default)
        survive. The issue asks a drag to clean up the order field of the
        *entire* collection, so after the library applies the move we renumber
        every row by its resulting position. ``order`` has no unique constraint,
        so the bulk update can't collide.
        """
        super()._update_order(updated_items, extra_model_filters)
        field = self.default_order_field
        rows = list(
            self.model.objects.filter(**extra_model_filters).order_by(field, "pk")
        )
        renumbered = renumber(rows, field)
        self.model.objects.bulk_update(renumbered, [field])
        return len(renumbered)


@admin.register(Illustration)
class IllustrationAdmin(SortableProjectAdmin):
    pass


@admin.register(SketchbookSample)
class SketchbookSampleAdmin(SortableProjectAdmin):
    pass


class DragNewRowsInline(SortableTabularInline):
    """A sortable inline whose *unsaved* rows are drag-sortable too (#27).

    sortable2 only drives saved rows (``tr.has_original``): a row added via "Add
    another" has neither the class nor the handle markup, so you can't drag it
    until it's saved. ``inline_sortable_new.js`` promotes each new row on
    ``formset:added`` so sortable2's existing Sortable picks it up — see that
    file for the seam. Loaded via ``Media`` here so all four sortable inlines
    inherit it; the listener is global and no-ops outside ``fieldset.sortable``.
    """

    class Media:
        js = ("portfolio/inline_sortable_new.js",)


class ComicPageInline(DragNewRowsInline):
    """Drag-sortable page collection for a Comic; row order is the render order.

    sortable2 renders ``order`` as a hidden input updated by drag and
    auto-numbers a new page to the end of the comic on save, so the prior
    slice's manual prefill script and save-time backstop are gone.

    ``extra = 0``: pages are added on demand via "Add another" rather than
    showing an always-present blank row.
    """

    model = ComicPage
    extra = 0
    fields = ("order", "image")
    ordering = ("order", "id")


@admin.register(Comic)
class ComicAdmin(SortableProjectAdmin):
    """A comic plus its drag-sortable pages, authored inline."""

    inlines = [ComicPageInline]


class RequireVideoOrThumbnailFormSet(CustomInlineFormSet):
    """Require a storyboard to have *something to show*: at least one video or a
    manual thumbnail.

    The rule can't live on the model: the parent saves before its inline
    children, so ``Storyboard.videos`` is empty during model validation. It
    belongs here, where the pending video forms are visible and ``self.instance``
    already carries the thumbnail the main form just bound (admin builds the
    inline formsets against the saved-but-not-committed parent). A video row
    counts when it has data and isn't marked for deletion. Extends sortable2's
    ``CustomInlineFormSet`` so the drag-order plumbing (``default_order_*``)
    still works on this sortable inline.
    """

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        has_video = any(
            form.cleaned_data and not form.cleaned_data.get("DELETE", False)
            for form in self.forms
        )
        if not has_video and not self.instance.thumbnail:
            raise ValidationError(
                "A storyboard needs at least one video or a thumbnail."
            )


class StoryboardVideoInline(DragNewRowsInline):
    """Drag-sortable embedded videos; optional when a thumbnail is set.

    ``verbose_name`` drops the model's "Storyboard" prefix from the inline's
    labels (Django derives them from the class name otherwise).
    """

    model = StoryboardVideo
    formset = RequireVideoOrThumbnailFormSet
    extra = 0
    fields = ("order", "url")
    verbose_name = "video"
    verbose_name_plural = "videos"


class StoryboardDeckInline(DragNewRowsInline):
    """Drag-sortable embedded slide decks (optional)."""

    model = StoryboardDeck
    extra = 0
    fields = ("order", "url")
    verbose_name = "deck"
    verbose_name_plural = "decks"


class StoryboardPDFInline(DragNewRowsInline):
    """Drag-sortable uploaded files (optional)."""

    model = StoryboardPDF
    extra = 0
    fields = ("order", "file", "display_name")
    verbose_name = "PDF"
    verbose_name_plural = "PDFs"


class StoryboardAdminForm(forms.ModelForm):
    """Swaps the body's plain textarea for the CKEditor 5 widget (Slice 12).

    Widget on the admin form, not the model, so ``body`` stays a ``TextField``
    (no migration) and the editor is an admin-only concern. ``body`` is declared
    explicitly so it carries the widget while the admin still builds the rest of
    the fieldset (including the dynamically re-added ``order`` field).
    """

    body = forms.CharField(
        widget=CKEditor5Widget(config_name="default"), required=False
    )

    class Meta:
        model = Storyboard
        # All editable fields except ``order`` — SortableProjectAdmin.get_fields
        # owns order (omitted on the add form, re-appended on the change form).
        fields = [
            "title",
            "slug",
            "published",
            "featured",
            "thumbnail",
            "category",
            "body",
        ]


@admin.register(Storyboard)
class StoryboardAdmin(SortableProjectAdmin):
    """A storyboard plus its ordered video, deck, and PDF collections."""

    form = StoryboardAdminForm
    inlines = [StoryboardVideoInline, StoryboardDeckInline, StoryboardPDFInline]
