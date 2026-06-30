"""The real client IP behind Heroku's router — one rule, one place.

Both privilege boundaries throttle per client IP: the storyboard gate
(django-ratelimit, #31) and the admin login (django-axes, #32). Behind Heroku's
router ``REMOTE_ADDR`` is the router, not the visitor, so trusting it would pool
every request into one bucket — one attacker could lock out everyone, or the
limit is trivially shared. Heroku appends the connecting client's IP as the
*last* ``X-Forwarded-For`` hop; earlier entries are client-supplied and
spoofable, so the last hop is the only trustworthy one. Falls back to
``REMOTE_ADDR`` when no XFF header is present (local dev, or a non-proxied
request).
"""


def client_ip(request):
    """Return the trustworthy client IP: the last X-Forwarded-For hop."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.rsplit(",", 1)[-1].strip()
    return request.META.get("REMOTE_ADDR", "")
