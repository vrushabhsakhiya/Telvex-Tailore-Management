#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Run migrations (applies both default and main database aliases)
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput
