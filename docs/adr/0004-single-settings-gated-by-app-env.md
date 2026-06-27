# A single settings module gated by APP_ENV

Configuration lives in one `config/settings.py`, read entirely from environment
variables (12-factor). Environment-specific behaviour — HTTPS redirection, HSTS,
secure cookies, and hashed/manifest static files — is grouped behind a single
`APP_ENV` variable (`development` | `test` | `production`) rather than a separate
settings module per environment. `APP_ENV` is unset by default and resolves to
`production`; `.envrc` exports `development` for local work, and
`config/test_settings.py` injects `test` before importing the base module.

`DEBUG` is derived from `APP_ENV` (on unless production) but can still be
overridden explicitly, so a developer can reproduce production-style error pages
locally without enabling the https redirect.

## Considered Options

- **Key hardening on `DEBUG` (original)** — rejected: overloaded `DEBUG` (a
  Django dev-tooling flag) as the prod/dev switch, and since `DEBUG` defaults to
  false, *absence of config* silently meant production. A bare `runserver` with
  no `.env` emitted a cacheable 301 to https, and the test suite's outcome
  depended on whether `DEBUG` happened to be exported in the shell.
- **A settings package (`base`/`dev`/`test`/`prod`)** — the conventional "Two
  Scoops" layout, rejected for now: more files and a base-import dance for
  variation that is currently small, and it trades the env-var posture for a
  module-swap posture (`DJANGO_SETTINGS_MODULE` per environment).
- **`APP_ENV` defaulting to `development`** — rejected: dev would "just work"
  everywhere, but an unconfigured deploy would silently ship `DEBUG=True` with no
  HTTPS. We preferred secure-by-omission, closing the resulting local/test gaps
  with `.envrc`, the test shim, and a boot-time assertion.

## Consequences

- Production is hardened even when an operator forgets to set `APP_ENV`. To stop
  a misconfigured deploy booting with placeholders, the production branch raises
  `ImproperlyConfigured` if `SECRET_KEY` is still the insecure default or
  `ALLOWED_HOSTS` contains `*`.
- The static manifest backend (`CompressedManifestStaticFilesStorage`) is active
  only in production, so dev and tests render templates without first running
  `collectstatic`.
- Tests cannot set `APP_ENV` from `pytest.ini` or a `conftest.py` fixture — both
  run after Django imports settings — so `config/test_settings.py` exists solely
  to set the variable before importing the base module. `pytest.ini` points
  `DJANGO_SETTINGS_MODULE` at it.
- `test` currently behaves identically to `development`; a dedicated `test`
  branch is justified only once a genuinely test-only setting appears (e.g. a
  faster password hasher).
