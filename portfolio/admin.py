from django.contrib import admin

from .models import Illustration


@admin.register(Illustration)
class IllustrationAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "order", "featured", "published", "updated_at")
    list_editable = ("order", "featured", "published")
    list_filter = ("published", "featured")
    search_fields = ("title",)
    ordering = ("order", "title")
    prepopulated_fields = {"slug": ("title",)}
