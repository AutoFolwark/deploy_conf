"""
Single source for the dev stack `docker compose` arguments (base + dev overlay + profile).

Keep in sync with Makefile `DOCKER_COMPOSE` for ENV=dev and with comments in dev/docker-compose.dev.yml.
"""

from __future__ import annotations

# Everything after `docker compose` for the local dev project (repo-root cwd).
COMPOSE_DEV_ARGV: list[str] = [
    "--profile",
    "embedded-datastores",
    "-f",
    "general/docker-compose.base.yml",
    "-f",
    "dev/docker-compose.dev.yml",
]
