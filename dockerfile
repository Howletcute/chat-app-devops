# Dockerfile
FROM python:3.12-slim-bookworm 
# Keep updated base image

WORKDIR /app

# Install OS packages needed for psycopg2 build and netcat (for entrypoint wait)
# Also install runtime dependencies like libpq5
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev netcat-openbsd libpq5 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (ensure all necessary parts are included)
# Copy the app package, migrations, config, run script, entrypoint
COPY app ./app
COPY migrations ./migrations
COPY config.py .
COPY run.py .
COPY entrypoint.sh /entrypoint.sh 
COPY templates ./templates
COPY static ./static

# Copy script to root

# Make entrypoint executable (redundant if chmod done locally, but safe)
RUN chmod +x /entrypoint.sh

# Expose the port Gunicorn will run on inside the container
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_CONFIG=prod 
# Default to production config in container

# Set the entrypoint script to run when container starts
ENTRYPOINT ["/entrypoint.sh"]
# Default command passed to the entrypoint script (exec "$@")
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:5000", "run:app"]
