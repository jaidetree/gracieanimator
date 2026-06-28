"""Mocked tests for the oembed-client boundary (ADR-0002).

Every test patches ``portfolio.oembed.urlopen`` so no real network call is made,
while still exercising endpoint construction and response parsing. Fixtures mirror
the real provider response shapes (html / width / height / thumbnail_url).
"""

import json
from contextlib import contextmanager
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from portfolio import oembed
from portfolio.oembed import OEmbed, OEmbedError

# --- response fixtures (real oembed shapes) ---

VIMEO_RESPONSE = {
    "provider_name": "Vimeo",
    "html": '<iframe src="https://player.vimeo.com/video/12345"></iframe>',
    "width": 1280,
    "height": 720,
    "thumbnail_url": "https://i.vimeocdn.com/video/12345_1280x720",
}
YOUTUBE_RESPONSE = {
    "provider_name": "YouTube",
    "html": '<iframe src="https://www.youtube.com/embed/abc"></iframe>',
    "width": 1280,
    "height": 720,
    "thumbnail_url": "https://i.ytimg.com/vi/abc/hqdefault.jpg",
}
SPEAKERDECK_RESPONSE = {
    "provider_name": "Speakerdeck",
    "html": '<iframe src="https://speakerdeck.com/player/xyz"></iframe>',
    "width": 710,
    "height": 596,
}


@contextmanager
def _stub_response(body: bytes):
    yield BytesIO(body)


@pytest.fixture
def fake_urlopen(monkeypatch):
    """Patch the module's urlopen; the returned setter installs a behavior."""

    def install(*, json_body=None, raw_body=None, error=None):
        calls = []

        def _urlopen(request, timeout=None):
            calls.append(request)
            if error is not None:
                raise error
            body = raw_body if raw_body is not None else json.dumps(json_body).encode()
            return _stub_response(body)

        monkeypatch.setattr(oembed, "urlopen", _urlopen)
        return calls

    return install


# --- success: video providers carry a poster ---


def test_vimeo_returns_embed_with_poster(fake_urlopen):
    fake_urlopen(json_body=VIMEO_RESPONSE)
    result = oembed.fetch("https://vimeo.com/12345")
    assert isinstance(result, OEmbed)
    assert result.provider == "vimeo"
    assert result.html == VIMEO_RESPONSE["html"]
    assert (result.width, result.height) == (1280, 720)
    # Vimeo's extension-less thumbnail gets ".jpg" appended (legacy quirk).
    assert result.poster_url == VIMEO_RESPONSE["thumbnail_url"] + ".jpg"


def test_youtube_returns_thumbnail_verbatim_as_poster(fake_urlopen):
    fake_urlopen(json_body=YOUTUBE_RESPONSE)
    result = oembed.fetch("https://www.youtube.com/watch?v=abc")
    assert result.provider == "youtube"
    assert result.poster_url == YOUTUBE_RESPONSE["thumbnail_url"]


def test_youtube_short_link_is_recognised(fake_urlopen):
    fake_urlopen(json_body=YOUTUBE_RESPONSE)
    assert oembed.fetch("https://youtu.be/abc").provider == "youtube"


# --- success: non-video provider has no poster ---


def test_speakerdeck_returns_embed_without_poster(fake_urlopen):
    fake_urlopen(json_body=SPEAKERDECK_RESPONSE)
    result = oembed.fetch("https://speakerdeck.com/user/talk")
    assert result.provider == "speakerdeck"
    assert result.html == SPEAKERDECK_RESPONSE["html"]
    assert result.poster_url is None


# --- request construction ---


def test_request_targets_provider_endpoint_with_encoded_url(fake_urlopen):
    calls = fake_urlopen(json_body=VIMEO_RESPONSE)
    oembed.fetch("https://vimeo.com/12345")
    full_url = calls[0].full_url
    assert full_url.startswith("https://vimeo.com/api/oembed.json?")
    assert "url=https%3A%2F%2Fvimeo.com%2F12345" in full_url
    assert "format=json" in full_url


# --- failure modes (AC: success / provider failure / malformed) ---


def test_unknown_provider_raises(fake_urlopen):
    with pytest.raises(OEmbedError, match="No oembed provider"):
        oembed.fetch("https://example.com/whatever")


def test_network_failure_raises(fake_urlopen):
    fake_urlopen(error=URLError("connection refused"))
    with pytest.raises(OEmbedError, match="request failed"):
        oembed.fetch("https://vimeo.com/12345")


def test_http_error_status_raises(fake_urlopen):
    http_error = HTTPError(
        url="https://vimeo.com/api/oembed.json",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=None,
    )
    fake_urlopen(error=http_error)
    with pytest.raises(OEmbedError, match="request failed"):
        oembed.fetch("https://vimeo.com/12345")


def test_malformed_json_raises(fake_urlopen):
    fake_urlopen(raw_body=b"<html>not json</html>")
    with pytest.raises(OEmbedError, match="not valid JSON"):
        oembed.fetch("https://vimeo.com/12345")


def test_response_missing_html_raises(fake_urlopen):
    fake_urlopen(json_body={"width": 640, "height": 480})
    with pytest.raises(OEmbedError, match="no embed HTML"):
        oembed.fetch("https://vimeo.com/12345")
