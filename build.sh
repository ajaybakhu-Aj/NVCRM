#!/bin/bash
# Build script for Vercel deployment

echo "Building project..."
python -m pip install -r requirements.txt

echo "Make Migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo "Collect Static..."
python manage.py collectstatic --noinput --clear
