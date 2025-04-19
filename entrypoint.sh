#!/bin/sh
# entrypoint.sh

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Optional: Wait for PostgreSQL to be ready ---
# This script waits until it can establish a basic TCP connection to the DB host/port.
# Requires 'nc' (netcat) installed in the Docker image.
# Read host/port from environment variables set in web-deployment.yaml
db_host=${DB_HOST:-postgres-svc} # Default to service name if var not set
db_port=${DB_PORT:-5432}       # Default PG port

echo "Waiting for postgres at ${db_host}:${db_port}..."
# Loop until 'nc' succeeds connecting to the host/port
# Timeout after 60 attempts (e.g., 30 seconds if sleep is 0.5)
attempts=0
max_attempts=60
while ! nc -z "${db_host}" "${db_port}" && [ $attempts -lt $max_attempts ]; do
  attempts=$((attempts+1))
  echo "Postgres not ready yet (attempt ${attempts}/${max_attempts})... waiting 0.5s"
  sleep 0.5
done
if [ $attempts -eq $max_attempts ]; then
   echo "Error: Timed out waiting for PostgreSQL."
   exit 1
fi
echo "PostgreSQL started!"
# --- End Optional Wait ---


# --- Run database migrations ---
echo "Running database migrations..."
# Ensure Flask context is set correctly for the commands
export FLASK_APP=run:app
# flask db upgrade # Apply any pending migrations

# --- Execute the main container command (CMD in Dockerfile) ---
# "$@" passes along any arguments from the Dockerfile CMD
echo "Starting application server..."
exec "$@"