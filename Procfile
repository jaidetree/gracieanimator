# Heroku process types (Slice 13). collectstatic runs at build time; the CSS is
# pre-compiled and committed (see .gitignore), so the dyno needs no Tailwind.
# `createcachetable` (idempotent) provisions the DB cache the storyboard-gate rate
# limiter counts in (Slice 31), so deploys never serve /auth/ against a missing table.
release: python manage.py migrate --noinput && python manage.py createcachetable
web: gunicorn config.wsgi
