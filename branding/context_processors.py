import random

from .models import Logo

# Today's `primary` brand color. Used when the pool is empty so a fresh install
# (or an emptied pool) looks like the site does now (#34).
DEFAULT_ACCENT = "#9E2820"


def branding(request):
    """Per-session logo + accent color, chosen once and sticky for the session.

    Mirrors ``pages.context_processors.nav_pages``: reads the stored ``logo_id``
    from ``request.session`` and, if it's absent or no longer resolves to an
    active logo, picks a uniform-random active logo and writes the id back. Only
    the id is stored — the ``Logo`` row stays the source of truth, so an owner's
    edit shows up immediately (#36).

    Fallbacks: an empty pool returns ``logo=None`` + ``DEFAULT_ACCENT`` (base.html
    then renders the visible text ``<h1>``); a stale/inactive session id is
    treated as unassigned and re-picked.
    """
    logo = _session_logo(request)
    if logo is None:
        logo = _pick_active_logo()
        if logo is not None:
            request.session["logo_id"] = logo.id
    accent = logo.accent_color if logo is not None else DEFAULT_ACCENT
    return {"logo": logo, "accent_color": accent}


def _session_logo(request):
    """The active logo the session already points at, or ``None`` if unset or
    stale (the id now names an inactive or deleted logo)."""
    logo_id = request.session.get("logo_id")
    if logo_id is None:
        return None
    return Logo.objects.filter(id=logo_id, is_active=True).first()


def _pick_active_logo():
    """A uniform-random active logo, or ``None`` when the pool is empty. Picking
    over a materialized list keeps selection deterministic under a monkeypatched
    ``random.choice`` in tests."""
    active = list(Logo.objects.filter(is_active=True))
    return random.choice(active) if active else None
