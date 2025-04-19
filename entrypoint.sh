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
while ! nc -z "${db_host}" "${db_port}" && [ $attempts -lt $max_attempts ]; # [cite: 419]
do
  attempts=$((attempts+1)) # [cite: 420]
  echo "Postgres not ready yet (attempt ${attempts}/${max_attempts})... waiting 0.5s" # [cite: 420]
  sleep 0.5 # [cite: 420]
done
if [ $attempts -eq $max_attempts ]; then # [cite: 421]
   echo "Error: Timed out waiting for PostgreSQL." # [cite: 421]
   exit 1 # [cite: 421]
fi
echo "PostgreSQL started!" # [cite: 421]
# --- End Optional Wait ---


# --- Run database migrations ---
echo "Running database migrations within app context..."
# Use python -c to import the app factory and run db upgrade inside app_context()
# Make sure run.py correctly imports and creates the app object [cite: 469]
python -c 'from run import app; from flask_migrate import upgrade; app.app_context().push(); upgrade()'

echo "Database migrations finished."


# --- Execute the main container command (CMD in Dockerfile) ---
# "$@" passes along any arguments from the Dockerfile CMD
echo "Starting application server..."
exec "$@" # [cite: 422]