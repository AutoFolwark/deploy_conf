#!/usr/bin/env python3
"""
Verify Redis connectivity for auth / api / calculator logical DBs.

Bundled stack uses one `redis` container; REDIS_URL uses different DB indices (/0 /1 /2).
With CHECK_DATABASES_USE_COMPOSE=1/true, runs `docker compose exec redis redis-cli -n N ping`
(same dev compose argv as the Postgres check; Infisical / pg_stack_up.sh).

Otherwise (demo / external Redis) uses a single `REDIS_URL` base (no /N suffix); checks
`${REDIS_URL}/0`, `/1`, `/2` via a short-lived `redis:8-alpine` client container.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from .compose_check_cmd import compose_check_cmd

# (label, logical_db_index) — must match general/docker-compose.base.yml REDIS_URL paths
COMPOSE_DB_INDICES: list[tuple[str, int]] = [
    ("auth", 0),
    ("api", 1),
    ("calculator", 2),
]

URL_LABELS = ("auth", "api", "calculator")


def _check_compose_db(repo: Path, label: str, db_index: int) -> None:
    cmd = compose_check_cmd() + [
        "exec",
        "-T",
        "redis",
        "redis-cli",
        "-n",
        str(db_index),
        "ping",
    ]
    subprocess.run(cmd, check=True, cwd=repo)


def _check_tcp_url(url: str, label: str) -> None:
    if not url or not url.strip():
        print(f"check_redis_service_urls: empty URL for {label}", file=sys.stderr)
        raise subprocess.CalledProcessError(1, "url")
    parsed = urlparse(url)
    if parsed.scheme not in ("redis", "rediss"):
        print(f"check_redis_service_urls: bad scheme for {label}: {url}", file=sys.stderr)
        raise subprocess.CalledProcessError(1, "url")
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "redis:8-alpine",
            "redis-cli",
            "-u",
            url,
            "ping",
        ],
        check=True,
    )


def main() -> None:
    repo = Path(__file__).resolve().parent.parent.parent
    os.chdir(repo)

    use_compose = os.environ.get("CHECK_DATABASES_USE_COMPOSE", "").lower() in (
        "1",
        "true",
        "yes",
        "y",
    )

    failed = False

    if use_compose:
        for label, db_index in COMPOSE_DB_INDICES:
            print(f"redis check [{label}] logical DB {db_index} ...", flush=True)
            try:
                _check_compose_db(repo, label, db_index)
            except subprocess.CalledProcessError:
                print(f"redis check [{label}] FAILED", file=sys.stderr)
                failed = True
    else:
        base = os.environ.get("REDIS_URL")
        if not base or not str(base).strip():
            print(
                "check_redis_service_urls: set REDIS_URL (base, e.g. redis://host:6379) "
                "or CHECK_DATABASES_USE_COMPOSE=1 for bundled redis",
                file=sys.stderr,
            )
            sys.exit(1)
        base = str(base).strip().rstrip("/")
        for i, label in zip((0, 1, 2), URL_LABELS):
            url = f"{base}/{i}"
            print(f"redis check [{label}] REDIS_URL/{i} ...", flush=True)
            try:
                _check_tcp_url(url, label)
            except subprocess.CalledProcessError:
                print(f"redis check [{label}] FAILED", file=sys.stderr)
                failed = True

    if failed:
        sys.exit(1)
    print("redis check: auth / api / calculator URLs OK", flush=True)


if __name__ == "__main__":
    main()
