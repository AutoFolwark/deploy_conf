"""Shared `docker compose` argv for check_postgres_service_dbs and check_redis_service_urls."""

from __future__ import annotations

from .compose_dev_argv import COMPOSE_DEV_ARGV


def compose_check_cmd() -> list[str]:
    """Argv prefix: ``docker compose ...`` (same project as Makefile dev stack)."""
    return ["docker", "compose", *COMPOSE_DEV_ARGV]
