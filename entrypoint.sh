#!/bin/sh
set -e

echo "Waiting for DB..."
until nc -z "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}"; do
  sleep 1
done

if [ "$#" -gt 0 ]; then
  echo "Applying migrations (noinput)..."
  python3 -m app migrate --noinput
  exec "$@"
fi

echo "Running migrations..."
python3 -m app makemigrations
python3 -m app migrate

echo "Starting server..."
exec python3 -m app runserver 0.0.0.0:8000
