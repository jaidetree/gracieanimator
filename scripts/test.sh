#!/usr/bin/env bash
# Run the test suite against local dev/staging resources. The shell may export a
# DATABASE_URL / R2_* pointing at the deployed Postgres and object store; strip
# them so pytest falls back to the project-local socket (postgres:///gracie) and
# in-repo media, keeping the suite hermetic and off shared infrastructure.
set -euo pipefail
cd "$(dirname "$0")/.."
exec env -u DATABASE_URL \
  -u R2_BUCKET_NAME \
  -u R2_ACCESS_KEY_ID \
  -u R2_SECRET_ACCESS_KEY \
  -u R2_ENDPOINT_URL \
  -u R2_CUSTOM_DOMAIN \
  pytest "$@"
