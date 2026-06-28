from adminsortable2.admin import (
    CustomInlineFormSet,
    SortableAdminMixin,
    SortableTabularInline,
)
from django.contrib import admin
from django.core.exceptions import ValidationError

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
        renumbered = []
        for position, obj in enumerate(rows, start=1):
            if getattr(obj, field) != position:
                setattr(obj, field, position)
                renumbered.append(obj)
        self.model.objects.bulk_update(renumbered, [field])
        return len(renumbered)


@admin.register(Illustration)
class IllustrationAdmin(SortableProjectAdmin):
    pass


@admin.register(SketchbookSample)
class SketchbookSampleAdmin(SortableProjectAdmin):
    pass


class ComicPageInline(SortableTabularInline):
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


class RequireOneVideoFormSet(CustomInlineFormSet):
    """Enforce the "at least one video" rule on the storyboard change form.

    The rule can't live on the model: the parent saves before its inline
    children, so ``Storyboard.videos`` is empty during model validation. It
    belongs here, where the pending inline forms are visible. A row counts when
    it has data and isn't marked for deletion. Extends sortable2's
    ``CustomInlineFormSet`` so the drag-order plumbing (``default_order_*``)
    still works on this sortable inline.
    """

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        live = [
            form
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False)
        ]
        if not live:
            raise ValidationError("A storyboard requires at least one video.")


class StoryboardVideoInline(SortableTabularInline):
    """Drag-sortable embedded videos; at least one is required."""

    model = StoryboardVideo
    formset = RequireOneVideoFormSet
    extra = 0
    fields = ("order", "url")


class StoryboardDeckInline(SortableTabularInline):
    """Drag-sortable embedded slide decks (optional)."""

    model = StoryboardDeck
    extra = 0
    fields = ("order", "url")


class StoryboardPDFInline(SortableTabularInline):
    """Drag-sortable uploaded files (optional)."""

    model = StoryboardPDF
    extra = 0
    fields = ("order", "file", "display_name")


@admin.register(Storyboard)
class StoryboardAdmin(SortableProjectAdmin):
    """A storyboard plus its ordered video, deck, and PDF collections."""

    inlines = [StoryboardVideoInline, StoryboardDeckInline, StoryboardPDFInline]
