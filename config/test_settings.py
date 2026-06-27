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

from config.settings import *  # noqa: E402,F401,F403
