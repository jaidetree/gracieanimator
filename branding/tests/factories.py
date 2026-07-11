import factory
from django.core.files.uploadedfile import SimpleUploadedFile

from branding.models import Logo


class LogoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Logo

    name = factory.Sequence(lambda n: f"Logo {n}")
    image = factory.LazyFunction(
        lambda: SimpleUploadedFile("logo.png", b"img-bytes", content_type="image/png")
    )
    accent_color = "#9E2820"
    is_active = True
