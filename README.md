#CurioCrate - Application Setup Guide
This guide will walk you through the steps to set up and run the CurioCrate application locally using Docker.

Table of Contents
Prerequisites

Setup Instructions

Clone the Repository

Navigate to the Project Directory

Build and Run Docker Containers

Apply Database Migrations



Setup Instructions
Follow these steps to get CurioCrate up and running:

1. Clone the Repository
First, clone the CurioCrate repository from GitHub to your local machine:

git clone git@github.com:Ahmed-Anwar-2001/CurioCrate.git

2. Navigate to the Project Directory
Change into the newly cloned project directory:

cd CurioCrate

3. Build and Run Docker Containers
This command will build the Docker images (if they don't exist or need rebuilding), create the necessary containers, and start them in detached mode (-d). It also specifies to use the .env file for environment variables.

Note: Ensure you have a .env file in the root of your CurioCrate directory with the necessary environment variables for your application (e.g., database credentials, secret keys).

docker compose --env-file ./.env up --build -d

4. Apply Database Migrations
Once the containers are running, you need to apply the database migrations to set up the database schema.

First, create the migration files based on your models:

docker compose --env-file ./.env exec web python manage.py makemigrations

Then, apply these migrations to your database:

docker compose --env-file ./.env exec web python manage.py migrate

Your CurioCrate application should now be set up and running! You can access it via the ports configured in your docker-compose.yml file (e.g., http://localhost:8000 if it's a Django app).
