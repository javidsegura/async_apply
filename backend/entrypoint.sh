#!/bin/sh
# Apply any pending migrations before serving, so a rebuilt image is never
# running against an older schema.
set -e

uv run alembic upgrade head
exec uv run uvicorn main:app --host 0.0.0.0 --port 8000
