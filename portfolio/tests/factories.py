import factory

from portfolio.models import Illustration


class IllustrationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Illustration

    title = factory.Sequence(lambda n: f"Illustration {n}")
    order = factory.Sequence(lambda n: n)
    published = True
    # A real (Pillow-generated) image so imagekit can produce renditions.
    image = factory.django.ImageField(width=1600, height=1200, format="JPEG")
