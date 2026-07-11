from django.core.validators import RegexValidator
from django.db import models

# 6- or 3-digit hex, no alpha. Both forms are valid CSS and are emitted verbatim
# into the `--color-accent` custom property (Spec #34), so the model refuses
# anything the stylesheet couldn't consume.
hex_color_validator = RegexValidator(
    regex=r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
    message="Enter a 3- or 6-digit hex color, e.g. #abc or #aabbcc.",
)


class Logo(models.Model):
    """A brand logo the owner can drop into the random per-visitor pool (#34).

    Each logo is paired with an ``accent_color`` chosen to match it. The image is
    served as the uploaded original (no imagekit rendition pyramid — logos are
    small) and stored on R2 like other media (ADR-0001). ``is_active`` gates
    eligibility for the random selection without deleting the row.
    """

    name = models.CharField(
        max_length=200,
        help_text="Admin-facing label to tell logos apart; not shown to visitors.",
    )
    image = models.ImageField(upload_to="logos/")
    accent_color = models.CharField(
        max_length=7,
        validators=[hex_color_validator],
        help_text="Hex color paired with this logo, e.g. #aabbcc or #abc.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive logos are excluded from the random pool.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
