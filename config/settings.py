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

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "pages",
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

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        # Manifest hashing only in prod; plain storage keeps dev/tests simple.
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if not IS_PROD
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
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
        raise ImproperlyConfigured("ALLOWED_HOSTS must not be '*' when APP_ENV=production")

    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
