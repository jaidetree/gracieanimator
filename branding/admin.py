from django.contrib import admin
from django.utils.html import format_html

from .models import Logo


@admin.register(Logo)
class LogoAdmin(admin.ModelAdmin):
    """Manage the random-logo pool. The owner eyeballs the logo↔color pairing
    from the list and toggles ``is_active`` inline (#35)."""

    list_display = ("name", "thumbnail", "swatch", "is_active")
    list_editable = ("is_active",)

    @admin.display(description="Preview")
    def thumbnail(self, obj):
        if not obj.image:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="height:40px;width:auto;" />', obj.image.url
        )

    @admin.display(description="Accent")
    def swatch(self, obj):
        return format_html(
            '<span title="{0}" style="display:inline-block;width:24px;height:24px;'
            'border:1px solid #ccc;background:{0};"></span> {0}',
            obj.accent_color,
        )
