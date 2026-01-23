#!/usr/bin/env bash

set -o errexit

pip install -r requirements.txt

# Remove old migration files (keeps __init__.py)
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# Recreate fresh migrations from current models
python manage.py makemigrations

# Collect static files
python manage.py collectstatic --noinput

# Apply migrations
python manage.py migrate --noinput
# set -o errexit

# pip install -r requirements.txt
# python manage.py collectstatic --noinput
# python manage.py migrate --noinput

# python manage.py runserver 0.0.0.0:8000
# uvicorn config.asgi:application --host 0.0.0.0 --port 8000
# daphne -b 0.0.0.0 -p 8000 config.asgi:application
