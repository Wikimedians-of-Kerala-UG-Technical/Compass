"""WSGI entry point: `gunicorn -c gunicorn.conf.py wsgi:app` (run from backend/)."""
from app import create_app

app = create_app()
