# Dockerfile

# 1. Use an official Python runtime
FROM python:3.9-slim

# 2. Set the working directory
WORKDIR /app

# 3. Copy requirements first and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.python.org -r requirements.txt

# 4. Copy the rest of the application code (app.py, templates/)
COPY . .

# 5. Make port 5000 available
EXPOSE 5000

# 6. Define environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# 7. Define the command to run app using gunicorn with eventlet worker
# Bind to 0.0.0.0:5000 inside the container
# Use 1 worker (-w 1) for simplicity for now
# 'app:app' tells gunicorn to load the 'app' instance from the 'app.py' file
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:5000", "app:app"]
