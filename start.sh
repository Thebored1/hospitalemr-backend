#!/usr/bin/env bash
set -euo pipefail

: "${PORT:=10000}"

WEB_CONCURRENCY="${WEB_CONCURRENCY:-1}"
GUNICORN_THREADS="${GUNICORN_THREADS:-2}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-180}"

exec gunicorn hospital_project.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --worker-class gthread \
  --workers "${WEB_CONCURRENCY}" \
  --threads "${GUNICORN_THREADS}" \
  --timeout "${GUNICORN_TIMEOUT}" \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  --max-requests 1000 \
  --max-requests-jitter 100

