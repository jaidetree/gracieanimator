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
direnv allow          # loads the flake, creates .venv, installs requirements.txt
cp .env.example .env  # then edit as needed
./scripts/db-init.sh  # initialise + start the project-local Postgres cluster
./manage.py migrate
./manage.py createsuperuser
```

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

All config is read from environment variables (see `.env.example`). `DEBUG`
toggles development vs production behaviour. Python dependencies live in
`requirements.txt` (installed into `.venv` by direnv); the Nix flake only
provides the toolchain (Python, Postgres, Tailwind CLI, uv).
