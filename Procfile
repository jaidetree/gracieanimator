# Heroku process types (Slice 13). collectstatic runs at build time; the CSS is
# pre-compiled and committed (see .gitignore), so the dyno needs no Tailwind.
release: python manage.py migrate --noinput
web: gunicorn config.wsgi
