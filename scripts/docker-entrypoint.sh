#!/usr/bin/env bash
# ==================================================
# Botocharcoal — Docker Entrypoint
# Runs Alembic migrations before starting the app.
# ==================================================
set -e

echo "Waiting for database to be ready..."
until PGHOST="${POSTGRES_HOST:-postgres}" PGPORT="${POSTGRES_PORT:-5432}" PGUSER="${POSTGRES_USER:-botocharcoal}" PGDATABASE="${POSTGRES_DB:-botocharcoal}" psql -c "SELECT 1" >/dev/null 2>&1; do
    sleep 1
done
echo "Database is ready."

echo "Running Alembic migrations..."
alembic upgrade head
echo "Migrations complete."

exec "$@"
