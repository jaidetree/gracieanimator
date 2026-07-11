"""
Django settings for The Grace Space.

All configuration is read from the environment, exported by direnv from
`.envrc` (+ a gitignored `.envrc.local`); see `.envrc.local.example`.
`APP_ENV` (development | test | production) flips environment-specific
behaviour; it defaults to production when unset.
"""

from pathlib import Path

import dj_database_url
import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()

# Deployment environment, NODE_ENV-style. Unset resolves to production so an
# unconfigured deploy is hardened by default; .envrc exports "development" for
# local work and config/test_settings.py injects "test" for the suite.
APP_ENV = env("APP_ENV", default="production")
IS_PROD = APP_ENV == "production"

# DEBUG follows the environment but can be overridden explicitly.
DEBUG = env.bool("DEBUG", default=not IS_PROD)
SECRET_KEY = env("SECRET_KEY", default="dev-insecure-change-me")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# The single host search engines should consolidate ranking onto. The site is
# reachable from more than one domain (e.g. the herokuapp fallback host), which
# is duplicate content; every page declares its canonical URL on this host and
# the sitemap emits URLs here, so signals converge on one domain regardless of
# which host served the request. CANONICAL_HOST must also be in ALLOWED_HOSTS in
# the deploy that owns it, or the canonical target itself 400s.
CANONICAL_HOST = env("CANONICAL_HOST", default="gracieanimator.art")
CANONICAL_SCHEME = env("CANONICAL_SCHEME", default="https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "adminsortable2",
    "imagekit",
    "django_ckeditor_5",
    # Brute-force lockout on the Django admin login (Slice 32). Ships its own
    # migrations for the attempt/lockout tables (no cache backend, unlike #31).
    "axes",
    "branding",
    "pages",
    "portfolio",
]

# AxesStandaloneBackend must come *first*: it raises on a locked client before
# any real authentication happens, and otherwise returns None so ModelBackend
# (after it) does the actual credential check.
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Must follow AuthenticationMiddleware: it turns the PermissionDenied axes
    # raises on a locked client into the friendly lockout response.
    "axes.middleware.AxesMiddleware",
    # Tags responses on non-canonical hosts (herokuapp/preview) noindex so only
    # the custom domain is indexed; see core/seo.py.
    "core.seo.noindex_non_canonical_host",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "pages.context_processors.nav_pages",
                "core.seo.canonical",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        # No host in the URL: psycopg falls back to PGHOST (an absolute path to
        # the project-local socket dir, exported by .envrc). A relative
        # `host=.pg` would be treated as a DNS name, not a socket dir.
        default=env("DATABASE_URL", default="postgres:///gracie"),
        conn_max_age=600,
    )
}

# Storyboards are gated behind a single shared password (Slice 9). A correct POST
# to /auth/ sets a session flag that unlocks every storyboard page for the
# browser session; an empty password (unset) never unlocks (see the login view).
STORYBOARDS_PASSWORD = env("STORYBOARDS_PASSWORD", default="")

# End the session — and thus storyboard access — when the browser closes, so the
# gate re-locks on a fresh browser without an explicit logout.
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# The storyboard gate is rate-limited (Slice 31) by django-ratelimit, which
# counts attempts in this cache. A shared, cross-process store is required for the
# limit to actually bind: the default per-process LocMemCache is per-dyno and
# resets on restart, so a brute-force grind would just spread across dynos. The DB
# cache (one low-traffic site, no Redis addon) holds across dynos and survives a
# restart within the window. Its table is provisioned by `createcachetable` — run
# in the Heroku release phase (Procfile) and once locally (see README).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "ratelimit_cache",
    }
}

# Brute-force lockout on the Django admin login (Slice 32, django-axes). The admin
# is a `django.contrib.auth` login, so axes hooks the auth backend + failure
# signals directly (unlike the hand-rolled storyboard gate, throttled by
# django-ratelimit in #31). Counts live in axes' own DB tables (its migrations);
# no cache backend is involved here.
#
# On in production by default (fail-secure, matching the settings posture); off in
# dev/test so a local typo-storm or the suite's many-POST admin tests don't lock
# anyone out. A dev can force it on with AXES_ENABLED=true. Override via env.
AXES_ENABLED = env.bool("AXES_ENABLED", default=IS_PROD)
# A handful of misses is fine; the (limit+1)-th attempt for the key is blocked.
AXES_FAILURE_LIMIT = env.int("AXES_FAILURE_LIMIT", default=5)
# Lock on the username+IP *combination* (nested list = AND): a single username
# isn't lockable from anywhere at once (admin-account DoS), and one bad actor on a
# shared IP doesn't lock out an innocent user on the same IP.
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
# The lockout self-clears after an hour; `manage.py axes_reset` unlocks manually.
AXES_COOLOFF_TIME = 1
# A correct login under the limit clears the failure count for that key (default
# keeps it), so an honest fat-finger streak doesn't shorten the next real session.
AXES_RESET_ON_SUCCESS = True
# Resolve the real client IP exactly as the storyboard gate does — the last
# X-Forwarded-For hop Heroku appends. django-ipware isn't installed, so without
# this axes would fall back to REMOTE_ADDR (the Heroku router) and lock every
# admin out behind one shared IP. One rule, one place: config.client_ip.
AXES_CLIENT_IP_CALLABLE = "config.client_ip.client_ip"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Opt into Django 6.0's URLField behaviour now: blank-scheme URLs entered in
# admin/forms are normalised to https:// rather than http://. Transitional
# setting, removable once we're on Django 6.0 where https is the default.
FORMS_URLFIELD_ASSUME_HTTPS = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Uploaded media (artwork) lives on Cloudflare R2 in any real deploy (ADR-0001):
# Heroku's filesystem is ephemeral, so uploads and imagekit renditions must not
# touch local disk. R2 is S3-compatible, reached via django-storages + boto3.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# R2 is enabled by presence of a bucket name; everything else is read from env.
# When unset (local dev, tests) the default storage stays on the local
# filesystem, so neither requires R2 credentials or a network round-trip.
R2_BUCKET_NAME = env("R2_BUCKET_NAME", default="")
R2_ENABLED = bool(R2_BUCKET_NAME)

if R2_ENABLED:
    default_storage = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": R2_BUCKET_NAME,
            "endpoint_url": env("R2_ENDPOINT_URL"),
            "access_key": env("R2_ACCESS_KEY_ID"),
            "secret_key": env("R2_SECRET_ACCESS_KEY"),
            # R2 ignores regions but boto3 requires one; "auto" is R2's value.
            "region_name": "auto",
            "signature_version": "s3v4",
            # R2 has no ACLs and serves a public portfolio: no per-object ACL,
            # and plain (unsigned) URLs so cached <img> src stays stable.
            "default_acl": None,
            "querystring_auth": False,
            # Don't clobber a same-named upload; keep distinct objects.
            "file_overwrite": False,
            # Optional public hostname (custom domain or pub-*.r2.dev) that
            # serves the bucket; when set, media URLs point here instead of the
            # private account endpoint.
            "custom_domain": env("R2_CUSTOM_DOMAIN", default="") or None,
        },
    }
else:
    default_storage = {"BACKEND": "django.core.files.storage.FileSystemStorage"}

STORAGES = {
    # Media: R2 in deploys, local filesystem otherwise (see above).
    "default": default_storage,
    # Static (CSS/JS) is always served by WhiteNoise, independent of media.
    # Manifest hashing only in prod; plain storage keeps dev/tests simple.
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if not IS_PROD
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

# WYSIWYG rich body (Slice 12). CKEditor 5 edits Page and Storyboard bodies in
# the admin; the stored HTML is sanitized on each model's save() (see richtext).
#
# Inline image uploads POST to django_ckeditor_5's upload view, which writes to
# STORAGES["default"] — so uploads land on R2 in any real deploy (ADR-0001) with
# no extra config, and on the local filesystem in dev/tests. Uploads are staff-
# only (the package default, made explicit here).
#
# mediaEmbed.previewsInData stores the provider <iframe> in the body (not the
# unrenderable <oembed url>), so embeds display on the public page as-is.
CKEDITOR_5_FILE_UPLOAD_PERMISSION = "staff"

CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": [
            "heading",
            "|",
            "bold",
            "italic",
            "link",
            "bulletedList",
            "numberedList",
            "blockQuote",
            "|",
            "imageUpload",
            "mediaEmbed",
            "insertTable",
            "|",
            "undo",
            "redo",
        ],
        "image": {
            "toolbar": [
                "imageTextAlternative",
                "|",
                "imageStyle:alignLeft",
                "imageStyle:full",
                "imageStyle:alignRight",
            ],
            "styles": ["full", "alignLeft", "alignRight"],
        },
        "table": {
            "contentToolbar": ["tableColumn", "tableRow", "mergeTableCells"],
        },
        "mediaEmbed": {"previewsInData": True},
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Production hardening, gated on APP_ENV (not DEBUG) so a dev can run with
# DEBUG off locally without triggering the https redirect.
if IS_PROD:
    # Because production is the default (unset) environment, fail loudly rather
    # than boot a public deploy with insecure placeholders.
    if SECRET_KEY == "dev-insecure-change-me":
        raise ImproperlyConfigured("SECRET_KEY must be set when APP_ENV=production")
    if "*" in ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            "ALLOWED_HOSTS must not be '*' when APP_ENV=production"
        )
    # Local-disk media is wiped on every dyno restart (ADR-0001); a production
    # deploy without R2 would silently lose every upload, so fail loudly.
    if not R2_ENABLED:
        raise ImproperlyConfigured("R2_BUCKET_NAME must be set when APP_ENV=production")

    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Default to the one-year max-age the HSTS preload list requires; greenfield
    # deploy, so there's no already-cached shorter policy to ramp up from, and the
    # only subdomain (media.) is HTTPS. A cautious deploy can still ramp via the
    # env var — and `preload` is advertised only when the value actually qualifies,
    # so a ramped-down override can never emit a preload directive it can't honour.
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS >= 31536000
