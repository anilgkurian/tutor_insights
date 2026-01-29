#!/bin/sh
set -e

export INSIGHTS_DB_URL="sqlite:///./db/tutor_insights.db"

echo "Running DB migrations..."
alembic upgrade head

echo "Starting app..."
exec uvicorn src.main:app --host 0.0.0.0 --port 4502
