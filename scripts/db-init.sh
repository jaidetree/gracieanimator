#!/usr/bin/env bash
# Initialise and start a project-local Postgres cluster under .pg/.
# Relies on PGDATA / PGHOST / PGPORT exported by .envrc.
set -euo pipefail

if [ ! -d "$PGDATA" ]; then
  echo "Initialising Postgres cluster at $PGDATA"
  initdb --auth=trust --no-locale --encoding=UTF8 "$PGDATA" >/dev/null
fi

if ! pg_ctl status >/dev/null 2>&1; then
  echo "Starting Postgres (socket: $PGHOST)"
  pg_ctl start -o "-k '$PGHOST' -p $PGPORT -c listen_addresses=''" -l "$PGHOST/server.log" -w
fi

if ! psql -lqt | cut -d'|' -f1 | grep -qw gracie; then
  echo "Creating database 'gracie'"
  createdb gracie
fi

echo "Postgres ready."
