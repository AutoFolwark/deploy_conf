#!/usr/bin/env python3
"""
Preflight: проверка подключений к БД сервисов (Postgres) и Redis (логические DB 0/1/2).

Вызывается из scripts/pg_stack_up.sh после `infisical run`. Переменные окружения — те же,
что у модулей в initialize_db_users/ (CHECK_DATABASES_USE_COMPOSE, DB_HOST, REDIS_URL,
POSTGRES_USER/POSTGRES_PASSWORD для автосоздания ролей и БД при ошибке подключения, …).
"""
from __future__ import annotations

import os
from pathlib import Path

from initialize_db_users.check_postgres_service_dbs import main as postgres_main
from initialize_db_users.check_redis_service_urls import main as redis_main

_REPO = Path(__file__).resolve().parent.parent


def main() -> None:
    os.chdir(_REPO)
    postgres_main()
    redis_main()


if __name__ == "__main__":
    main()
