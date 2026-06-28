"""Live integration tests for the oembed client — opt-in, hit real providers.

Skipped by default (pytest.ini sets `-m "not live"`); run explicitly with:

    pytest -m live

These exist because the mocked suite (test_oembed.py) cannot prove the
real-world quirks: that Vimeo's poster URL actually resolves once ".jpg" is
appended, that the whitelisted Referer is still accepted, and that each
provider's live response shape still parses. A failure here may simply mean one
of the URLs below rotted (deleted/privated) rather than a code regression —
check the URL before assuming the client broke.

The URLs are arbitrary, stable, *public* content chosen for longevity, NOT
Gracie's portfolio (which is password-gated / under NDA and must never appear in
the repo).
"""

from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest

from portfolio import oembed

pytestmark = pytest.mark.live

VIMEO_URL = "https://vimeo.com/336753042"
YOUTUBE_URL = "https://www.youtube.com/watch?v=eWkgDjZkG6E"
SPEAKERDECK_URL = (
    "https://speakerdeck.com/neunhofferart/"
    "edgar-and-the-haunted-cucumber-individual-boards-2018"
)


def _is_fetchable_image(url: str) -> bool:
    """True if a HEAD/GET to the poster URL returns a 2xx — proves it resolves."""
    request = Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300
    except URLError:
        return False


def _assert_embed(result, expected_provider):
    assert result.provider == expected_provider
    assert result.html  # non-empty embed markup
    assert result.width > 0 and result.height > 0


def test_vimeo_live_resolves_with_loadable_poster():
    result = oembed.fetch(VIMEO_URL)
    _assert_embed(result, "vimeo")
    # The whole point: the ".jpg"-appended Vimeo poster must actually load.
    assert result.poster_url and result.poster_url.endswith(".jpg")
    assert _is_fetchable_image(result.poster_url)


def test_youtube_live_resolves_with_loadable_poster():
    result = oembed.fetch(YOUTUBE_URL)
    _assert_embed(result, "youtube")
    assert result.poster_url
    assert _is_fetchable_image(result.poster_url)


def test_speakerdeck_live_resolves_without_poster():
    result = oembed.fetch(SPEAKERDECK_URL)
    _assert_embed(result, "speakerdeck")
    assert result.poster_url is None
