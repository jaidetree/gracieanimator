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
./manage.py createsuperuser
```

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

## Test

```sh
pytest
```

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
