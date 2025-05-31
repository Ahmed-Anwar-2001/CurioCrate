# Use a Python base image suitable for production
FROM python:3.10-slim-buster

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for psycopg2 and potentially other packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project directory into the container
COPY . /app/CurioCrate

# Set the new working directory to the inner Django project folder
WORKDIR /app/CurioCrate

# Collect static files into a volume-mounted directory
RUN python manage.py collectstatic --noinput

# Expose the port Gunicorn will listen on
EXPOSE 8000

# Command to run Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "CurioCrate.wsgi:application"]