# Dockerfile

# 1. Use an official Python runtime as a parent image
# Using 'slim' variant for a smaller image size
FROM python:3.9-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy the requirements file into the container at /app
COPY requirements.txt .

# 4. Install any needed packages specified in requirements.txt
# --no-cache-dir avoids storing cache, keeping the image smaller
# --trusted-host pypi.python.org helps if there are network issues accessing PyPI sometimes
RUN pip install --no-cache-dir --trusted-host pypi.python.org -r requirements.txt

# 5. Copy the rest of the application code (app.py) into the container at /app
COPY . .

# 6. Make port 5000 available to the world outside this container
# (Flask app runs on port 5000 as defined in app.py)
EXPOSE 5000

# 7. Define environment variables needed by the app (Optional but good practice)
# These can be overridden when running the container
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0 
# Ensures Flask listens externally within the container
# Note: DB connection vars will be set via docker-compose or Kubernetes later

# 8. Define the command to run your app using CMD
# This will execute 'python app.py' when the container launches
CMD ["python", "app.py"]