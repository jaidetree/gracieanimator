"""The Storyboard password gate (Slice 9): one shared secret, one module.

Storyboards sit behind a single shared password. A correct POST to /auth/ sets a
browser-session flag that unlocks every storyboard page; the gallery views guard
themselves with ``@storyboards_required`` and never name the session key. Keeping
the key, the decorator, and the login/logout views together means the one shared
secret lives in exactly one place.
"""

from functools import wraps

from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.crypto import constant_time_compare
from django.utils.http import url_has_allowed_host_and_scheme
from django_ratelimit.decorators import ratelimit

from config import url_names
from config.client_ip import client_ip

# A correct POST to /auth/ sets this session flag, which unlocks every storyboard
# page for the browser session; the guarded views require it.
SESSION_AUTH_KEY = "storyboards_auth"

# How many /auth/ POSTs one client IP may make per minute before being blocked.
# Generous enough that a real visitor fat-fingering the password is never caught,
# tight enough that a shared-secret brute-force can't grind at dyno speed (#31).
AUTH_RATE = "5/m"


def client_ip_key(group, request):
    """ratelimit key: the real client IP behind Heroku (the last XFF hop).

    The "which hop to trust" rule lives in one place, ``config.client_ip``, so the
    gate (here) and the admin-login throttle (django-axes, #32) can't drift apart
    on the security-critical question of which forwarded entry is spoofable.
    ``@ratelimit`` passes a ``(group, request)`` key signature; axes passes just
    ``request`` — both delegate to the same ``client_ip``.
    """
    return client_ip(request)


def storyboards_required(view):
    """Redirect to the storyboard login form unless the session is unlocked.

    The flag is browser-session scoped (``SESSION_EXPIRE_AT_BROWSER_CLOSE``), so
    one unlock covers every storyboard page until the browser closes or /logout/.
    The originally requested path rides along as ``next`` so login returns there.
    """

    @wraps(view)
    def guarded(request, *args, **kwargs):
        if request.session.get(SESSION_AUTH_KEY):
            return view(request, *args, **kwargs)
        login_url = reverse(url_names.STORYBOARD_AUTH)
        return redirect(f"{login_url}?next={request.path}")

    return guarded


@ratelimit(key=client_ip_key, rate=AUTH_RATE, method="POST", block=False)
def storyboards_login(request):
    """The password gate: GET shows the form, a correct POST unlocks the session.

    The shared password is read from settings; an unset (empty) password never
    unlocks, so a misconfigured deploy fails closed rather than open. The check is
    constant-time so a network observer can't recover the secret a character at a
    time. On success the session key is cycled (defeating session fixation), the
    flag is set, and the visitor is sent to a safe ``next`` (their original
    destination) or the storyboards index.

    POSTs are rate-limited per client IP (``@ratelimit`` above). With
    ``block=False`` the decorator only flags ``request.limited`` rather than
    raising, so an over-limit attempt is handled here: it renders the friendly form
    with a 429 and never reaches the password check — failing closed regardless of
    what was submitted.
    """
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = reverse(url_names.STORYBOARD_GALLERY)

    error = None
    status = 200
    if request.method == "POST":
        if getattr(request, "limited", False):
            error = "Too many attempts. Please wait a minute and try again."
            status = 429
        else:
            password = settings.STORYBOARDS_PASSWORD
            submitted = request.POST.get("password") or ""
            if password and constant_time_compare(submitted, password):
                request.session.cycle_key()
                request.session[SESSION_AUTH_KEY] = True
                return redirect(next_url)
            error = "Incorrect password."

    return render(
        request,
        "portfolio/storyboards_login.html",
        {"next": next_url, "error": error, "page_title": "Storyboards"},
        status=status,
    )


def storyboards_logout(request):
    """Clear the session flag (re-locking the storyboards) and return to login."""
    request.session.pop(SESSION_AUTH_KEY, None)
    return redirect(reverse(url_names.STORYBOARD_AUTH))
