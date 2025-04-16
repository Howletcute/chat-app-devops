# Dockerfile

# 1. Use an official Python runtime
FROM python:3.9-slim

# 2. Set the working directory
WORKDIR /app

# 3. Copy requirements first and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.python.org -r requirements.txt

# 4. Copy the rest of the application code, including templates
COPY . .

# 5. Make port 5000 available
EXPOSE 5000

# 6. Define environment variables (optional but good practice)
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1 
# Ensure logs appear immediately

# 7. Define the command to run app with eventlet
# Use eventlet directly as recommended by Flask-SocketIO docs for deployment
CMD ["eventlet", "wsgi.py"]