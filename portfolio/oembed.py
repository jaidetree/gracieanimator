"""oembed-client: the single boundary for external provider HTTP (ADR-0002).

Given a Vimeo / YouTube / Speakerdeck URL, resolve the provider's oembed API to
the embed HTML, its dimensions, and — for videos — a poster image. Every network
call the app makes to a provider lives in this module, so it can be mocked in one
place and the consumer (storyboard save, a later slice) never touches HTTP.

Failures are surfaced as ``OEmbedError`` for callers to handle (ADR-0002: a save
must not be blocked by a flaky provider); this module never swallows them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Some providers (Vimeo) gate oembed on a referring domain; kept from the legacy
# Squarespace stack, which is the referer Vimeo has whitelisted for this account.
_REFERER = "https://gracieanimator.squarespace.com"
# Speakerdeck 403s the default "Python-urllib" agent; a browser-like UA is
# required there and harmless to Vimeo/YouTube.
_USER_AGENT = "Mozilla/5.0 (compatible; GracieAnimator/1.0)"
_TIMEOUT = 10
# Dimensions we request; the response echoes the provider's actual values, which
# are what we cache and use for aspect-ratio padding.
_WIDTH, _HEIGHT = 1280, 720


class OEmbedError(Exception):
    """A provider URL could not be resolved to a usable oembed result."""


@dataclass(frozen=True)
class OEmbed:
    """A resolved oembed response. ``poster_url`` is set for videos only."""

    provider: str
    html: str
    width: int
    height: int
    poster_url: str | None = None


@dataclass(frozen=True)
class _Provider:
    name: str
    endpoint: str
    is_video: bool
    domains: tuple[str, ...]


# Match order is irrelevant — domains are disjoint.
_PROVIDERS = (
    _Provider(
        name="vimeo",
        endpoint="https://vimeo.com/api/oembed.json",
        is_video=True,
        domains=("vimeo.com",),
    ),
    _Provider(
        name="youtube",
        endpoint="https://www.youtube.com/oembed",
        is_video=True,
        domains=("youtube.com", "youtu.be"),
    ),
    _Provider(
        name="speakerdeck",
        endpoint="https://speakerdeck.com/oembed.json",
        is_video=False,
        domains=("speakerdeck.com",),
    ),
)


def fetch(url: str) -> OEmbed:
    """Resolve a provider URL to its oembed result.

    Raises ``OEmbedError`` for an unrecognised provider, a network/HTTP failure,
    a non-JSON body, or a response missing the required embed HTML.
    """
    provider = _provider_for(url)
    if provider is None:
        raise OEmbedError(f"No oembed provider recognised for URL: {url}")

    data = _get_json(provider.endpoint, url)
    return _parse(provider, data)


def _provider_for(url: str) -> _Provider | None:
    return next(
        (p for p in _PROVIDERS if any(d in url for d in p.domains)),
        None,
    )


def _get_json(endpoint: str, url: str) -> dict:
    query = urlencode(
        {"url": url, "format": "json", "width": _WIDTH, "height": _HEIGHT}
    )
    request = Request(
        f"{endpoint}?{query}",
        headers={"Referer": _REFERER, "User-Agent": _USER_AGENT},
    )
    try:
        with urlopen(request, timeout=_TIMEOUT) as response:
            body = response.read()
    except URLError as error:  # connection refused, timeout, non-2xx HTTPError
        raise OEmbedError(f"oembed request failed for {url}: {error}") from error

    try:
        return json.loads(body)
    except (ValueError, TypeError) as error:
        raise OEmbedError(f"oembed response was not valid JSON for {url}") from error


def _parse(provider: _Provider, data: dict) -> OEmbed:
    html = data.get("html")
    if not html:
        raise OEmbedError(f"oembed response from {provider.name} had no embed HTML")

    return OEmbed(
        provider=provider.name,
        html=html,
        width=data.get("width", _WIDTH),
        height=data.get("height", _HEIGHT),
        poster_url=_poster_url(provider, data),
    )


def _poster_url(provider: _Provider, data: dict) -> str | None:
    if not provider.is_video:
        return None
    thumbnail = data.get("thumbnail_url")
    if not thumbnail:
        return None
    # Legacy real-world quirk: Vimeo's oembed thumbnail_url comes back without a
    # file extension and 404s unless ".jpg" is appended. Replicated verbatim from
    # the prior stack; unverified against live here (mocked slice) — confirm when
    # the storyboard consumer lands.
    if provider.name == "vimeo":
        return f"{thumbnail}.jpg"
    return thumbnail
