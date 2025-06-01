# CurioCrate - Application Setup Guide

This guide will walk you through the steps to set up and run the CurioCrate application locally using Docker.

## 📚 Table of Contents
- [Setup Instructions](#setup-instructions)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Navigate to the Project Directory](#2-navigate-to-the-project-directory)
  - [3. Build and Run Docker Containers](#3-build-and-run-docker-containers)
  - [4. Apply Database Migrations](#4-apply-database-migrations)

## 🛠️ Setup Instructions

Follow these steps to get **CurioCrate** up and running on your local machine:

### 1. Clone the Repository
```bash
git clone --single-branch --branch master git@github.com:Ahmed-Anwar-2001/CurioCrate.git
```

### 2. Navigate to the Project Directory
```bash
cd CurioCrate
```

### 3. Build and Run Docker Containers
Make sure you have a `.env` file in the root directory with required environment variables (e.g., database credentials, secret keys).

```bash
docker compose --env-file ./.env up --build -d
```

### 4. Apply Database Migrations

**Create migration files:**
```bash
docker compose --env-file ./.env exec web python manage.py makemigrations
```

**Apply migrations:**
```bash
docker compose --env-file ./.env exec web python manage.py migrate
```

## ✅ All Set!

Your **CurioCrate** application should now be running locally. You can access it via the ports configured in your `docker-compose.yml` file (e.g., [http://localhost:8000](http://localhost:8000)).

Happy coding! 🚀
