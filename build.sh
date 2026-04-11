#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Run migrations (applies both default and main database aliases)
echo "----------------------------------------"
echo "RUNNING MIGRATIONS..."
python manage.py migrate --noinput || { echo "MIGRATION FAILED!"; exit 1; }
echo "MIGRATIONS SUCCESSFUL"
echo "----------------------------------------"

# Collect static files
echo "COLLECTING STATIC FILES..."
python manage.py collectstatic --noinput
echo "BUILD COMPLETE"
