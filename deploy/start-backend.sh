#!/bin/sh
set -eu

# A failed migration stops startup; do not serve against an outdated schema.
alembic upgrade head
exec "$@"
