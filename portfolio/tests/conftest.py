import pytest

from portfolio import oembed


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Isolate uploads and imagekit cache files in a per-test temp dir."""
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture(autouse=True)
def stub_oembed(request, monkeypatch):
    """Keep model saves off the network by default.

    ``OEmbedMedia.save`` resolves the URL through ``oembed.fetch`` on create
    (pk is None), so any factory-built video/deck would hit a real provider.
    Patch the shared module attribute to a canned result; tests that exercise
    the oembed/unreachable paths override ``portfolio.oembed.fetch`` locally.

    The ``oembed`` modules test ``fetch`` itself, so they opt out — they patch
    the lower ``urlopen`` seam and must see the real ``fetch``.
    """
    if "test_oembed" in request.module.__name__:
        return

    def _fetch(url):
        return oembed.OEmbed(
            provider="vimeo",
            html=f'<iframe src="{url}"></iframe>',
            width=1280,
            height=720,
            poster_url="https://i.vimeocdn.com/video/stub.jpg",
        )

    monkeypatch.setattr(oembed, "fetch", _fetch)
