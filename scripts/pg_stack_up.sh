#!/usr/bin/env bash
# Start stack with preflight Postgres + Redis checks (scripts/initialize.py).
# Invoked from Makefile after `infisical run`. CHECK_DATABASES_USE_COMPOSE should be set per env in Infisical
# (dev: 1, demo: 0); if unset, this script defaults it so manual runs still work.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ENV_NAME="${1:-dev}"

# Same argv as initialize_db_users/compose_dev_argv.py (single source of truth).
mapfile -t COMPOSE_DEV < <(PYTHONPATH="$ROOT/scripts" python3 -c "from initialize_db_users.compose_dev_argv import COMPOSE_DEV_ARGV; print('\n'.join(COMPOSE_DEV_ARGV))")

dc_dev() {
  docker compose "${COMPOSE_DEV[@]}" "$@"
}

dc_demo() {
  docker compose -f demo/docker-compose.demo.yml "$@"
}

case "$ENV_NAME" in
  dev)
    dc_dev up -d --wait --wait-timeout 120 postgres redis
    export CHECK_DATABASES_USE_COMPOSE="${CHECK_DATABASES_USE_COMPOSE:-1}"
    python3 "$ROOT/scripts/initialize.py"
    dc_dev up -d
    ;;
  demo)
    export CHECK_DATABASES_USE_COMPOSE="${CHECK_DATABASES_USE_COMPOSE:-0}"
    python3 "$ROOT/scripts/initialize.py"
    dc_demo up -d
    ;;
  prod)
    echo "pg_stack_up.sh: prod is unchanged; use: infisical run --env=prod -- docker compose -f prod/docker-compose.yml up -d" >&2
    exit 1
    ;;
  *)
    echo "usage: $0 {dev|demo}" >&2
    exit 1
    ;;
esac
