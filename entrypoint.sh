#!/bin/sh

set -e

echo "Entrypoint script started. Applying database migrations..."

python manage.py migrate

exec "$@"