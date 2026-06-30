"""Settings for the test suite.

config.settings defaults APP_ENV to "production" and derives both
SECURE_SSL_REDIRECT and the static files storage backend from it *at import
time*. The test client talks plain http and renders templates without a built
static manifest, so it needs the non-production variants. Injecting APP_ENV here,
before importing the base settings, is the only reliable point to steer those
import-time decisions — a conftest fixture runs too late, and pytest.ini cannot
set an env var before Django configures.
"""

import os

os.environ["APP_ENV"] = "test"
# A known storyboard password for the suite. HTTP-seam tests still set it
# explicitly with override_settings; this default exists for the Playwright E2E,
# whose live_server reads settings in a thread where override_settings is fiddly.
os.environ.setdefault("STORYBOARDS_PASSWORD", "test-storyboards-password")

from config.settings import *  # noqa: E402,F401,F403

# Rate limiting off by default so the gate's many-POST suites (#30) don't trip the
# limiter and bleed counts across tests. The rate-limit tests (#31) opt back in
# per-test with `settings.RATELIMIT_ENABLE = True` and a cleared cache.
RATELIMIT_ENABLE = False

# Admin-login lockout (#32) off by default so the many-POST admin suites don't
# lock themselves out; the axes tests opt back in per-test with
# `settings.AXES_ENABLED = True` against fresh attempt rows.
AXES_ENABLED = False
