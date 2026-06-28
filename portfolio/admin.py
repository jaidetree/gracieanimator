from django.contrib import admin
from django.db.models import Max

from .models import Category, Comic, ComicPage, Illustration, SketchbookSample


def _next_order(queryset):
    """The order to assign a new row: highest existing order + 1 (1 when empty).

    Maxed over *all* rows in the queryset (published or not) so a new piece can
    never collide with a hidden one's order. Slots a fresh row at the end.
    """
    current_max = queryset.aggregate(Max("order"))["order__max"]
    return (current_max or 0) + 1


class OrderedAdminMixin:
    """Auto-assign the next display order to a new piece left at order 0.

    Keeps ``order`` a manual field but spares the editor from hunting the next
    number: a new instance saved with the default 0 lands at the end of its
    type. An explicit non-zero order is always respected.
    """

    def save_model(self, request, obj, form, change):
        if not change and obj.order == 0:
            obj.order = _next_order(type(obj).objects.all())
        super().save_model(request, obj, form, change)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Storyboard grouping labels; slug prepopulated from the name."""

    list_display = ("name", "slug")
    search_fields = ("name",)
    ordering = ("name",)
    prepopulated_fields = {"slug": ("name",)}


class ImageProjectAdmin(OrderedAdminMixin, admin.ModelAdmin):
    """Shared admin config for single-image project types."""

    list_display = ("title", "slug", "order", "published", "featured", "updated_at")
    list_editable = ("order", "published", "featured")
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


class ComicPageInline(admin.TabularInline):
    """Ordered page collection for a Comic; row order follows the order field.

    A small admin script (``comic_page_order.js``) pre-fills the order field in
    a newly added inline row in the browser; ``ComicAdmin.save_formset`` is the
    server-side backstop that numbers any page still left at 0 on save.
    """

    model = ComicPage
    extra = 1
    fields = ("order", "image")
    ordering = ("order", "id")

    class Media:
        js = ("portfolio/comic_page_order.js",)


@admin.register(Comic)
class ComicAdmin(OrderedAdminMixin, admin.ModelAdmin):
    """A comic plus its ordered pages, authored inline."""

    list_display = ("title", "slug", "order", "published", "featured", "updated_at")
    list_editable = ("order", "published", "featured")
    list_filter = ("published", "featured")
    search_fields = ("title",)
    ordering = ("order", "title")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ComicPageInline]

    def save_formset(self, request, form, formset, change):
        """Number new comic pages left at order 0, continuing past existing pages.

        Scoped per comic and assigned in form order so several rows added at once
        get distinct, increasing values rather than all colliding at 1.
        """
        if formset.model is not ComicPage:
            super().save_formset(request, form, formset, change)
            return
        comic = form.instance
        next_order = _next_order(ComicPage.objects.filter(comic=comic))
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for instance in instances:
            if instance.pk is None and instance.order == 0:
                instance.order = next_order
                next_order += 1
            instance.save()
        formset.save_m2m()
