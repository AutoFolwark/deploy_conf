#!/usr/bin/env python3
"""
Verify that each microservice PostgreSQL role can connect to its database.

Reads credentials from the environment (e.g. injected by Infisical when run via
`infisical run -- ...`). Used by scripts/pg_stack_up.sh before `docker compose up`.

Modes:
  CHECK_DATABASES_USE_COMPOSE=1/true — run `docker compose exec` against the `postgres` service (local dev).
  Set per environment in Infisical; `scripts/pg_stack_up.sh` defaults it if unset (dev=1, demo=0).
  Otherwise — connect over TCP using DB_HOST (required), optional DB_PORT or PGPORT (default 5432).
  Demo / external Postgres. Uses a short-lived `postgres:17-alpine` client container so host
  `psql` is not required.

If connection fails and CHECK_DATABASES_AUTO_PROVISION is true (default: on for compose, off for TCP),
creates the role and database using POSTGRES_USER / POSTGRES_PASSWORD as superuser.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from .compose_check_cmd import compose_check_cmd

# (label, DB_USER env, DB_PASS env, DB_NAME env)
SERVICE_DBS: list[tuple[str, str, str, str]] = [
    ("auth", "AUTH_DB_USER", "AUTH_DB_PASS", "AUTH_DB_NAME"),
    ("api", "API_DB_USER", "API_DB_PASS", "API_DB_NAME"),
    ("notification", "NOTIFICATION_DB_USER", "NOTIFICATION_DB_PASS", "NOTIFICATION_DB_NAME"),
    ("carfax", "CARFAX_DB_USER", "CARFAX_DB_PASS", "CARFAX_DB_NAME"),
    ("payment", "PAYMENT_DB_USER", "PAYMENT_DB_PASS", "PAYMENT_DB_NAME"),
    ("calculator", "CALCULATOR_DB_USER", "CALCULATOR_DB_PASS", "CALCULATOR_DB_NAME"),
    ("favorites", "FAVORITES_DB_USER", "FAVORITES_DB_PASS", "FAVORITES_DB_NAME"),
    ("bid", "BID_DB_USER", "BID_DB_PASS", "BID_DB_NAME"),
    ("order", "ORDER_DB_USER", "ORDER_DB_PASS", "ORDER_DB_NAME"),
    ("file", "FILE_DB_USER", "FILE_DB_PASS", "FILE_DB_NAME"),
]

_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")


def _require(name: str) -> str:
    v = os.environ.get(name)
    if v is None or not str(v).strip():
        print(f"check_postgres_service_dbs: missing or empty {name}", file=sys.stderr)
        sys.exit(1)
    return str(v)


def _pg_ident(name: str, kind: str) -> str:
    if not _IDENT.match(name):
        print(
            f"check_postgres_service_dbs: invalid {kind} identifier {name!r} "
            "(use ASCII letters, digits, underscore only)",
            file=sys.stderr,
        )
        sys.exit(1)
    return name


def _auto_provision_enabled(use_compose: bool) -> bool:
    raw = os.environ.get("CHECK_DATABASES_AUTO_PROVISION")
    if raw is None or not str(raw).strip():
        return use_compose
    return str(raw).strip().lower() in ("1", "true", "yes", "y")


def _check_compose(repo: Path, user: str, password: str, database: str) -> None:
    cmd = compose_check_cmd() + [
        "exec",
        "-T",
        "-e",
        f"PGPASSWORD={password}",
        "postgres",
        "psql",
        "-U",
        user,
        "-d",
        database,
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        "SELECT 1",
    ]
    subprocess.run(cmd, check=True, cwd=repo)


def _check_tcp(host: str, port: str, user: str, password: str, database: str) -> None:
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-e",
            f"PGPASSWORD={password}",
            "postgres:17-alpine",
            "psql",
            f"-h{host}",
            f"-p{port}",
            "-U",
            user,
            "-d",
            database,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            "SELECT 1",
        ],
        check=True,
    )


def _psql_compose_admin(
    repo: Path, admin_user: str, admin_password: str, sql: str
) -> None:
    cmd = compose_check_cmd() + [
        "exec",
        "-T",
        "-e",
        f"PGPASSWORD={admin_password}",
        "postgres",
        "psql",
        "-U",
        admin_user,
        "-d",
        "postgres",
        "-v",
        "ON_ERROR_STOP=1",
    ]
    subprocess.run(cmd, input=sql.encode(), check=True, cwd=repo)


def _psql_tcp_admin(
    host: str, port: str, admin_user: str, admin_password: str, sql: str
) -> None:
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-i",
            "-e",
            f"PGPASSWORD={admin_password}",
            "postgres:17-alpine",
            "psql",
            f"-h{host}",
            f"-p{port}",
            "-U",
            admin_user,
            "-d",
            "postgres",
            "-v",
            "ON_ERROR_STOP=1",
        ],
        input=sql.encode(),
        check=True,
    )


def _db_exists_compose(
    repo: Path, admin_user: str, admin_password: str, database: str
) -> bool:
    _pg_ident(database, "database")
    esc = database.replace("'", "''")
    cmd = compose_check_cmd() + [
        "exec",
        "-T",
        "-e",
        f"PGPASSWORD={admin_password}",
        "postgres",
        "psql",
        "-U",
        admin_user,
        "-d",
        "postgres",
        "-t",
        "-A",
        "-c",
        f"SELECT 1 FROM pg_database WHERE datname = '{esc}';",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=repo)
    return r.returncode == 0 and "1" in r.stdout.strip()


def _db_exists_tcp(
    host: str, port: str, admin_user: str, admin_password: str, database: str
) -> bool:
    _pg_ident(database, "database")
    esc = database.replace("'", "''")
    r = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-e",
            f"PGPASSWORD={admin_password}",
            "postgres:17-alpine",
            "psql",
            f"-h{host}",
            f"-p{port}",
            "-U",
            admin_user,
            "-d",
            "postgres",
            "-t",
            "-A",
            "-c",
            f"SELECT 1 FROM pg_database WHERE datname = '{esc}';",
        ],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0 and "1" in r.stdout.strip()


def _sql_quoted_literal(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def _provision_role_sql(user: str, password: str) -> str:
    """
    PL/pgSQL block: CREATE ROLE or ALTER ROLE.
    (CREATE DATABASE cannot run inside DO).
    """
    u = _pg_ident(user, "user")
    return (
        "DO $body$\n"
        "DECLARE\n"
        f"  uname text := {_sql_quoted_literal(u)};\n"
        f"  pw text := {_sql_quoted_literal(password)};\n"
        "BEGIN\n"
        "  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = uname) THEN\n"
        "    EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L', uname, pw);\n"
        "  ELSE\n"
        "    EXECUTE format('ALTER ROLE %I WITH PASSWORD %L', uname, pw);\n"
        "  END IF;\n"
        "END\n"
        "$body$;\n"
    )


def _provision(
    repo: Path,
    use_compose: bool,
    host: str,
    port: str,
    user: str,
    password: str,
    database: str,
) -> None:
    admin_user = os.environ.get("POSTGRES_USER") or "postgres"
    admin_pass = _require("POSTGRES_PASSWORD")
    dbn = _pg_ident(database, "database")
    usr = _pg_ident(user, "user")

    sql_role = _provision_role_sql(user, password)
    if use_compose:
        print(
            f"check_postgres_service_dbs: provisioning role {usr!r} via {admin_user!r} ...",
            flush=True,
        )
        _psql_compose_admin(repo, admin_user, admin_pass, sql_role)
        exists = _db_exists_compose(repo, admin_user, admin_pass, database)
        if not exists:
            print(
                f"check_postgres_service_dbs: creating database {dbn!r} owner {usr!r} ...",
                flush=True,
            )
            create_db = f"CREATE DATABASE {dbn} OWNER {usr};"
            _psql_compose_admin(repo, admin_user, admin_pass, create_db)
    else:
        print(
            f"check_postgres_service_dbs: provisioning role {usr!r} via {admin_user!r} @ {host} ...",
            flush=True,
        )
        _psql_tcp_admin(host, port, admin_user, admin_pass, sql_role)
        exists = _db_exists_tcp(host, port, admin_user, admin_pass, database)
        if not exists:
            print(
                f"check_postgres_service_dbs: creating database {dbn!r} owner {usr!r} ...",
                flush=True,
            )
            create_db = f"CREATE DATABASE {dbn} OWNER {usr};"
            _psql_tcp_admin(host, port, admin_user, admin_pass, create_db)


def _try_check_then_provision(
    repo: Path,
    use_compose: bool,
    host: str,
    port: str,
    user: str,
    password: str,
    database: str,
    label: str,
    auto: bool,
) -> bool:
    try:
        if use_compose:
            _check_compose(repo, user, password, database)
        else:
            _check_tcp(host, port, user, password, database)
        return True
    except subprocess.CalledProcessError:
        if not auto:
            print(f"postgres check [{label}] FAILED", file=sys.stderr)
            return False
        print(
            f"postgres check [{label}] connection failed; attempting provision ...",
            file=sys.stderr,
            flush=True,
        )
        try:
            _provision(repo, use_compose, host, port, user, password, database)
        except subprocess.CalledProcessError as e:
            print(f"postgres check [{label}] provision FAILED: {e}", file=sys.stderr)
            return False
        try:
            if use_compose:
                _check_compose(repo, user, password, database)
            else:
                _check_tcp(host, port, user, password, database)
            print(f"postgres check [{label}] OK after provision", flush=True)
            return True
        except subprocess.CalledProcessError:
            print(
                f"postgres check [{label}] FAILED after provision",
                file=sys.stderr,
            )
            return False


def main() -> None:
    repo = Path(__file__).resolve().parent.parent.parent
    os.chdir(repo)

    use_compose = os.environ.get("CHECK_DATABASES_USE_COMPOSE", "").lower() in (
        "1",
        "true",
        "yes",
        "y",
    )

    if use_compose:
        host = ""
        port = ""
    else:
        host = _require("DB_HOST")
        port = os.environ.get("DB_PORT") or os.environ.get("PGPORT") or "5432"
        port = str(port).strip() or "5432"

    auto = _auto_provision_enabled(use_compose)
    failed = False
    for label, uk, pk, dk in SERVICE_DBS:
        user = _require(uk)
        password = _require(pk)
        database = _require(dk)
        print(f"postgres check [{label}] {user} -> {database} ...", flush=True)
        if not _try_check_then_provision(
            repo, use_compose, host, port, user, password, database, label, auto
        ):
            failed = True

    if failed:
        sys.exit(1)
    print("postgres check: all service databases OK", flush=True)


if __name__ == "__main__":
    main()
