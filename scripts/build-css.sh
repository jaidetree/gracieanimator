#!/usr/bin/env bash
# Compile Tailwind via the standalone CLI. Pass --watch for dev.
set -euo pipefail
cd "$(dirname "$0")/.."
exec tailwindcss -i ./assets/css/input.css -o ./static/css/stylesheet.css --minify "$@"
