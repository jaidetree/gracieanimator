# Security review (#30)

A pass over the attack surface of the Django rebuild to find vectors that need
hardening against common web attacks. Findings are ranked by real-world risk,
not by ease of fixing. Two low-risk defence-in-depth fixes ship with this review
(see *Hardened now*); the higher-impact operational items are recommendations for
a human to weigh, because they change production behaviour or add dependencies.

The threat model: a public, read-only portfolio. The only privilege boundaries
are (a) Django admin (staff authoring) and (b) the shared-password gate on
storyboards. There are no per-visitor accounts and no user-submitted content, so
the classic "untrusted input rendered to other users" surface is small.

## Baseline: Django deploy audit is clean

`manage.py check --deploy`, run under a production-like environment
(`APP_ENV=production` + a real-length `SECRET_KEY`/`ALLOWED_HOSTS`/`R2_*`),
reports **no issues**. This empirically confirms the prod hardening in
`config/settings.py` (the `if IS_PROD:` block): SSL redirect, HSTS, secure
session/CSRF cookies, `X-Frame-Options`, and content-type nosniff are all active.
Boot-time `ImproperlyConfigured` guards already fail a prod deploy closed if
`SECRET_KEY` is the dev placeholder, `ALLOWED_HOSTS` is `*`, or R2 is unset.

> Reproduce: `env -u DATABASE_URL -u R2_BUCKET_NAME ... APP_ENV=production
> SECRET_KEY=$(python -c 'import secrets;print(secrets.token_urlsafe(50))')
> ALLOWED_HOSTS=gracieanimator.art R2_BUCKET_NAME=x R2_ENDPOINT_URL=https://x
> R2_ACCESS_KEY_ID=x R2_SECRET_ACCESS_KEY=x python manage.py check --deploy`

## Findings, ranked by risk

### 1. Storyboard gate has no brute-force / rate limiting — top operational risk

A single shared password protects every storyboard page, checked on `POST /auth/`
with no attempt throttling, lockout, or CAPTCHA. For a *shared* secret this is the
genuinely exploitable vector: an attacker can grind guesses as fast as the dyno
answers. Impact is bounded (unlock only reveals the storyboard gallery, no
data-modifying or account surface), which is why it's a recommendation rather than
a same-day code change.

**Recommendation:** add request throttling on `/auth/` POST — `django-axes` or
`django-ratelimit` keyed on client IP, or a small hand-rolled per-IP cooldown in
the login view. Pair with a strong, high-entropy `STORYBOARDS_PASSWORD` so a
bounded guess rate can't succeed regardless. Deferred here because it adds a
dependency and an operational story (where lockout state lives) that a human
should choose.

### 2. HSTS max-age (3600s) contradicts `preload=True` — config inconsistency

`SECURE_HSTS_SECONDS` defaults to 3600 (1 hour) while `SECURE_HSTS_PRELOAD = True`.
The HSTS preload list requires `max-age` ≥ 31536000 (1 year), so the current
combination is internally inconsistent: it advertises preload intent the policy
can't honour, and one hour is short protection against SSL-stripping.

**Recommendation (not shipped):** raise the default to `31536000` once the deploy
is confirmed HTTPS-only on the apex and subdomains. **Intentionally left as a
human decision** — HSTS is hard to reverse (browsers cache it for the full
max-age; preload is effectively permanent), so it must not ride in silently inside
a review commit. It is already env-overridable via `SECURE_HSTS_SECONDS`.

### 3. Timing-unsafe password comparison — fixed (low real risk)

The gate compared `submitted == password` with Python's `==`, which short-circuits
on the first differing byte and is therefore timing-variable. Over a network,
recovering a *shared* gallery password through timing is close to unexploitable
(jitter dwarfs the signal), so this is defence-in-depth, not a headline. Fixed
because it's a one-line idiomatic improvement — see *Hardened now*.

### 4. No session-key cycling on unlock — fixed (low real risk)

The gate set the auth flag on the *existing* session id. A session-fixation
attacker who can plant a known session id on a victim could ride their later
unlock. Impact is low (the session grants only gallery viewing, no per-user
state), but cycling the key on auth is the standard, cheap fix — see *Hardened
now*.

## Considered and accepted (no change)

- **WYSIWYG body XSS — mitigated by `sanitize_html`.** Page/Storyboard bodies are
  rendered with `|safe`, but every `save()` runs the HTML through `nh3` with a
  fixed allowlist (`richtext.py`): scripts and event handlers are stripped, URL
  schemes are restricted to http(s)/mailto/tel (so `javascript:` dies), and inline
  CSS is limited to layout properties (no `expression()`/`url()`). `<iframe>` is
  allowed for provider embeds; authors are *trusted staff*, so an allowed iframe
  host is within the threat model.
- **oembed embed HTML rendered `|safe` un-sanitized.** `video.embed_html` /
  `deck.embed_html` come straight from the provider. Acceptable: the source is a
  hardcoded provider allowlist (Vimeo/YouTube/Speakerdeck), not visitor input.
- **oembed provider matching is substring, not host-based.** `_provider_for` tests
  `"vimeo.com" in url`, which also matches `vimeo.com.evil.com`. **Not an SSRF**:
  the URL the server actually fetches is the hardcoded provider `endpoint`; the
  attacker-influenced value rides only as a query parameter, so no internal host
  is ever reached. Worth tightening to a host check eventually for correctness,
  but not a vulnerability today.
- **Staff file/image uploads.** CKEditor's upload endpoint is staff-only
  (`CKEDITOR_5_FILE_UPLOAD_PERMISSION = "staff"`) and uploads land on R2, served
  from a separate origin/custom domain — so even a malicious SVG/HTML upload is
  sandboxed away from the app's origin and can't script against it.
- **Open redirect on `next`.** The gate validates `next` with
  `url_has_allowed_host_and_scheme` before redirecting; an external target is
  dropped in favour of the index (pinned by
  `test_external_next_is_ignored_in_favour_of_the_index`).
- **Media URLs are unsigned (`querystring_auth=False`).** Intentional — the
  portfolio is public and stable `<img src>` caching is desired; no private
  objects live in the bucket.

## Hardened now

`portfolio/storyboard_gate.py`, with tests in
`portfolio/tests/test_storyboard_gate.py`:

- **Constant-time password check** via `django.utils.crypto.constant_time_compare`
  (finding 3). The fail-closed empty-password guard (`if password and …`) is
  preserved, still pinned by `test_empty_configured_password_never_unlocks`.
- **Session-key cycling** via `request.session.cycle_key()` on successful unlock
  (finding 4); pinned by `test_successful_unlock_cycles_the_session_key`.
- **Missing-field robustness:** a POST omitting `password` coerces to `""` and
  fails closed instead of comparing `None`; pinned by
  `test_post_without_password_field_stays_locked`.
