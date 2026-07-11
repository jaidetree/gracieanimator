import factory

from branding.models import Logo


class LogoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Logo

    name = factory.Sequence(lambda n: f"Logo {n}")
    # A real PNG (not raw bytes) so the rendered <img> can read intrinsic
    # width/height for layout-shift protection (#36).
    image = factory.django.ImageField(width=120, height=40, format="PNG")
    accent_color = "#9E2820"
    is_active = True
