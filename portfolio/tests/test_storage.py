"""Storage-backend selection for Slice 3 (Cloudflare R2 via django-storages).

The default-storage choice is made at *import time* in config/settings.py from
env vars, so the env-driven branches are exercised by importing the settings
module in a clean subprocess with a controlled environment. The local-default
branch is just asserted against the already-loaded test settings.

What still needs live R2 credentials — the upload round-trip (object lands in the
bucket and is retrievable) — is out of scope here; these cover backend
selection, the media URL host, the prod guard, and statics staying on WhiteNoise.
"""
import json
import os
import subprocess
import sys

from django.conf import settings

R2_ENV = {
    "R2_BUCKET_NAME": "gracie-media",
    "R2_ENDPOINT_URL": "https://acct123.r2.cloudflarestorage.com",
    "R2_ACCESS_KEY_ID": "test-key-id",
    "R2_SECRET_ACCESS_KEY": "test-secret",
}

# Reports config.settings' storage decisions, then exits — or prints the
# exception type when settings refuse to load (the prod guard path).
_PROBE = """
import json
try:
    from config import settings as s
except Exception as e:
    print("ERROR:" + type(e).__name__ + ":" + str(e))
    raise SystemExit(0)
report = {
    "r2_enabled": s.R2_ENABLED,
    "default_backend": s.STORAGES["default"]["BACKEND"],
    "staticfiles_backend": s.STORAGES["staticfiles"]["BACKEND"],
}
default = s.STORAGES["default"]
if default.get("OPTIONS"):
    from storages.backends.s3 import S3Storage
    report["media_url"] = S3Storage(**default["OPTIONS"]).url("illustrations/x.jpg")
print(json.dumps(report))
"""


def _load_settings(**overrides):
    """Import config.settings in a subprocess under a controlled env.

    Returns (report_dict_or_None, raw_stdout). A clean env (R2_* and APP_ENV
    stripped, then overridden) keeps the host's direnv exports from leaking in.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("R2_")}
    env.pop("APP_ENV", None)
    env.update(overrides)
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True, text=True, env=env, cwd=settings.BASE_DIR,
    )
    out = proc.stdout.strip()
    report = None if out.startswith("ERROR:") else json.loads(out)
    return report, out


# --- local default (no R2 configured): the running test suite itself ---

def test_default_storage_is_local_without_r2():
    # The suite runs with no R2 vars, so media must stay on the local FS — no
    # network, no credentials needed for dev or tests.
    assert settings.R2_ENABLED is False
    assert settings.STORAGES["default"]["BACKEND"] == (
        "django.core.files.storage.FileSystemStorage"
    )


# --- R2 enabled by bucket presence (AC #1, #2) ---

def test_r2_bucket_selects_s3_backend():
    report, _ = _load_settings(APP_ENV="development", **R2_ENV)
    assert report["r2_enabled"] is True
    assert report["default_backend"] == "storages.backends.s3.S3Storage"


def test_media_url_served_from_r2_endpoint():
    # Without a custom domain, media URLs resolve against the R2 account
    # endpoint + bucket. NB this endpoint only answers signed requests; public
    # <img> serving needs R2_CUSTOM_DOMAIN (next test) + a public bucket.
    report, _ = _load_settings(APP_ENV="development", **R2_ENV)
    assert "acct123.r2.cloudflarestorage.com" in report["media_url"]
    assert "gracie-media" in report["media_url"]
    assert report["media_url"].endswith("illustrations/x.jpg")


def test_media_url_uses_custom_domain_when_set():
    report, _ = _load_settings(
        APP_ENV="development", R2_CUSTOM_DOMAIN="media.example.com", **R2_ENV
    )
    assert report["media_url"] == "https://media.example.com/illustrations/x.jpg"


# --- statics unaffected (AC #4) ---

def test_static_storage_unaffected_by_r2():
    report, _ = _load_settings(APP_ENV="development", **R2_ENV)
    # Media moved to R2, but static files stay on the WhiteNoise/Django backend.
    assert "storages.backends.s3" not in report["staticfiles_backend"]
    assert report["staticfiles_backend"] == (
        "django.contrib.staticfiles.storage.StaticFilesStorage"
    )


# --- prod guard: no silent local-disk media in production ---

def test_production_without_r2_refuses_to_boot():
    _, raw = _load_settings(
        APP_ENV="production", SECRET_KEY="x" * 50, ALLOWED_HOSTS="example.com"
    )
    assert raw.startswith("ERROR:ImproperlyConfigured")
    assert "R2_BUCKET_NAME" in raw


def test_production_with_r2_boots():
    report, _ = _load_settings(
        APP_ENV="production", SECRET_KEY="x" * 50,
        ALLOWED_HOSTS="example.com", **R2_ENV,
    )
    assert report["r2_enabled"] is True
    assert report["default_backend"] == "storages.backends.s3.S3Storage"
