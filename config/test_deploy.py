"""Deploy boot smoke test for Slice 13 (Heroku).

The Procfile's `web` process loads `config.wsgi:application`; if settings or app
loading raise under a production environment, the dyno never boots. This builds
that exact WSGI callable in a clean subprocess under production-like config —
the closest unit-level proxy for "the dyno boots". (config/test_settings.py runs
the suite as APP_ENV=test, so production import-time behaviour can only be
exercised out-of-process, the same technique as portfolio/tests/test_storage.py.)

It does not connect to Postgres: get_wsgi_application() runs app loading, not
queries, so no DATABASE_URL is needed here.
"""
import os
import subprocess
import sys

from django.conf import settings

PROD_ENV = {
    "APP_ENV": "production",
    "SECRET_KEY": "x" * 50,
    "ALLOWED_HOSTS": "grace-space-staging.herokuapp.com",
    "R2_BUCKET_NAME": "gracie-media",
    "R2_ENDPOINT_URL": "https://acct123.r2.cloudflarestorage.com",
    "R2_ACCESS_KEY_ID": "test-key-id",
    "R2_SECRET_ACCESS_KEY": "test-secret",
}

_PROBE = """
from config.wsgi import application
print("OK:" + type(application).__name__)
"""


def test_wsgi_application_boots_under_production_config():
    # Strip the host's direnv R2_*/APP_ENV exports, then inject a clean prod env.
    env = {k: v for k, v in os.environ.items() if not k.startswith("R2_")}
    env.pop("APP_ENV", None)
    env.update(PROD_ENV)
    env["DJANGO_SETTINGS_MODULE"] = "config.settings"
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True, text=True, env=env, cwd=settings.BASE_DIR,
    )
    assert proc.stdout.strip().startswith("OK:"), (
        f"WSGI app failed to load under production config:\n{proc.stderr}"
    )
