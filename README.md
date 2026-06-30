# The Grace Space

Gracie's portfolio site — a Django app with Postgres as the single source of
truth and the Django admin as the CMS. Content renders live from the database;
there is no build/cache step.

## Stack

- Django 5 + Postgres (via `dj-database-url` / `django-environ`)
- Standalone Tailwind CLI (no npm) for styling
- WhiteNoise for static files
- `pytest-django` + `factory-boy` for tests
- Nix flake + direnv for the dev environment

## Setup

The dev environment is provided by Nix + direnv. From the repo root:

```sh
direnv allow         # loads the flake, creates .venv, installs requirements.txt
./scripts/db start   # initialise + start the project-local Postgres cluster
./manage.py migrate
./manage.py createcachetable   # DB cache the storyboard-gate rate limiter counts in
./manage.py createsuperuser
```

`createcachetable` is idempotent; skip it and a `POST /auth/` (the storyboard
login) hits a missing-table error, since the rate limiter writes to the DB cache.

Local dev works with no extra config. For personal overrides (a real
`SECRET_KEY`, a different DB, etc.), `cp .envrc.local.example .envrc.local`,
edit, and re-run `direnv allow`.

## Run

```sh
./scripts/build-css.sh            # compile Tailwind once
./scripts/build-css.sh --watch    # or watch during development
./manage.py runserver
```

- Public site: http://localhost:8000/
- Admin: http://localhost:8000/admin/

The admin login is brute-force-locked by `django-axes` (Slice 32): 5 failed
logins for a username+IP lock that pair out for an hour. It's **off in dev/test**
(`AXES_ENABLED=IS_PROD`) so local typos never lock you out; set `AXES_ENABLED=true`
to exercise it. To clear a lockout manually (any env): `./manage.py axes_reset`.

## Test

```sh
make test
```

Wraps `pytest`, stripping any exported `DATABASE_URL` / `R2_*` so the suite runs
against the project-local Postgres socket and in-repo media rather than deployed
resources. Run `pytest` directly only when those vars are unset.

## Configuration

All config is read from the environment. The committed `.envrc` exports the
defaults (and direnv sources a gitignored `.envrc.local` for overrides — see
`.envrc.local.example`); production reads real config vars from the platform.
`APP_ENV` (`development` | `test` | `production`) selects environment-specific
behaviour such as HTTPS redirection and static-file hashing; it **defaults to
`production`** when unset, so `.envrc` exports `APP_ENV=development` and the test
suite injects `test`. Python dependencies live in `requirements.txt` (installed
into `.venv` by direnv); the Nix flake only provides the toolchain (Python,
Postgres, Tailwind CLI, uv).

## Deploy (Heroku)

The app deploys to Heroku via a [pipeline](https://devcenter.heroku.com/articles/pipelines):
a **staging** app **auto-deploys from the default branch** through the GitHub
integration (a production app + staging→prod promotion are added at go-live).

- `Procfile` — `web` runs gunicorn (`config.wsgi`, binding `$PORT`
  automatically); `release` runs `python manage.py migrate --noinput` then
  `python manage.py createcachetable` (idempotent) each deploy, the latter
  provisioning the DB cache the storyboard-gate rate limiter counts in.
- `.python-version` pins Python 3.12.
- Tailwind CSS is pre-compiled and committed (`static/css/stylesheet.css`), so
  the dyno needs no Node/Tailwind; Heroku's build-time `collectstatic` collects
  it and WhiteNoise serves it.

**Required config vars (set on the staging app *before the first push*)** —
Heroku runs `collectstatic` at build time, which imports `config/settings.py`
and trips its production guards, so a missing var fails the build, not just the
boot:

| Var | Notes |
| --- | --- |
| `SECRET_KEY` | required; boot refuses the dev placeholder |
| `ALLOWED_HOSTS` | the app's `*.herokuapp.com` host (comma-separated; **not** `*`) |
| `R2_BUCKET_NAME` | required in production (ADR-0001); ephemeral disk would lose uploads |
| `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` | R2 credentials |
| `R2_CUSTOM_DOMAIN` | optional public media host (custom domain or `pub-*.r2.dev`) |
| `DATABASE_URL` | provided automatically by the Heroku Postgres add-on |

`APP_ENV` can be left unset — it defaults to `production`, which is what staging
runs as.
