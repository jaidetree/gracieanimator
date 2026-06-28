# Task runner for The Grace Space. Thin wrapper over scripts/ + manage.py.
# Assumes the direnv/Nix shell is active (APP_ENV, PG* already exported).
.DEFAULT_GOAL := help
.PHONY: help dev serve css css-watch db-start db-stop db-status migrate superuser test lint format build release

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

dev: ## Tailwind watcher, and runserver together
	@trap 'kill 0' EXIT INT TERM; \
	./scripts/build-css.sh --watch & \
	./manage.py runserver & \
	wait

serve: ## Run the Django dev server only
	./manage.py runserver

css: ## Compile Tailwind once (minified)
	./scripts/build-css.sh

css-watch: ## Recompile Tailwind on change
	./scripts/build-css.sh --watch

db-start: ## Init (if needed) and start the project-local Postgres
	./scripts/db start

db-stop: ## Stop the project-local Postgres
	./scripts/db stop

db-status: ## Report Postgres status
	./scripts/db status

migrate: ## Apply database migrations
	./manage.py migrate

superuser: ## Create an admin user
	./manage.py createsuperuser

test: ## Run the test suite
	pytest

lint: ## Lint and check formatting (no changes)
	ruff check .
	ruff format --check .

format: ## Auto-fix lint issues and reformat
	ruff check --fix .
	ruff format .

build: ## Compile assets for production (CSS + collectstatic)
	./scripts/build-css.sh
	./manage.py collectstatic --noinput

release: ## Run migrations (Heroku release phase)
	./manage.py migrate
