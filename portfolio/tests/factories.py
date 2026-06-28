import factory

from portfolio.models import (
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


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")


class IllustrationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Illustration

    title = factory.Sequence(lambda n: f"Illustration {n}")
    order = factory.Sequence(lambda n: n)
    published = True
    # A real (Pillow-generated) image so imagekit can produce renditions.
    image = factory.django.ImageField(width=1600, height=1200, format="JPEG")


class SketchbookSampleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SketchbookSample

    title = factory.Sequence(lambda n: f"Sketchbook Sample {n}")
    order = factory.Sequence(lambda n: n)
    published = True
    # A real (Pillow-generated) image so imagekit can produce renditions.
    image = factory.django.ImageField(width=1600, height=1200, format="JPEG")


class ComicFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comic

    title = factory.Sequence(lambda n: f"Comic {n}")
    order = factory.Sequence(lambda n: n)
    published = True


class ComicPageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ComicPage

    comic = factory.SubFactory(ComicFactory)
    order = factory.Sequence(lambda n: n)
    # A real (Pillow-generated) image so imagekit can produce renditions.
    image = factory.django.ImageField(width=1200, height=1800, format="JPEG")


class StoryboardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Storyboard

    title = factory.Sequence(lambda n: f"Storyboard {n}")
    order = factory.Sequence(lambda n: n)
    published = True
    category = factory.SubFactory(CategoryFactory)


class StoryboardVideoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StoryboardVideo

    storyboard = factory.SubFactory(StoryboardFactory)
    order = factory.Sequence(lambda n: n)
    url = factory.Sequence(lambda n: f"https://vimeo.com/{n}")


class StoryboardDeckFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StoryboardDeck

    storyboard = factory.SubFactory(StoryboardFactory)
    order = factory.Sequence(lambda n: n)
    url = factory.Sequence(lambda n: f"https://speakerdeck.com/user/talk-{n}")


class StoryboardPDFFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StoryboardPDF

    storyboard = factory.SubFactory(StoryboardFactory)
    order = factory.Sequence(lambda n: n)
    display_name = factory.Sequence(lambda n: f"Brief {n}")
    file = factory.django.FileField(filename="brief.pdf", data=b"%PDF-1.4 test")


def make_comic(n_pages=3, **kwargs):
    """A published Comic with ``n_pages`` ordered pages."""
    comic = ComicFactory(**kwargs)
    for i in range(n_pages):
        ComicPageFactory(comic=comic, order=i)
    return comic
