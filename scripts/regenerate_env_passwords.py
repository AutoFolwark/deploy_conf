#!/usr/bin/env python3
"""
Regenerate password-style values in a .env file in place (with backup).

Rotates by default:
  - Any key ending with _PASS (e.g. API_DB_PASS, AUTH_DB_PASS)

Does not rotate (see DEFAULT_EXCLUDE_KEYS): SMTP app passwords, RabbitMQ user
password, admin header secret, shared DB passwords you set elsewhere, or API /
OAuth / cloud credentials (AWS_*, STRIPE_*, etc.) unless you pass --extra KEY.

Use DEFAULT_EXCLUDE_KEYS (below) and/or --exclude KEY to skip specific variables.
Excludes always win over --extra.

Usage:
  ./scripts/regenerate_env_passwords.py              # uses .env in cwd
  ./scripts/regenerate_env_passwords.py --file /path/to/.env
  ./scripts/regenerate_env_passwords.py --dry-run  # print planned changes only
  ./scripts/regenerate_env_passwords.py --exclude API_DB_PASS
"""

from __future__ import annotations

import argparse
import re
import secrets
import shutil
import string
import sys
from datetime import datetime, timezone
from pathlib import Path

# KEY=value — key is unquoted identifier at line start (ignore comments / blanks)
ENV_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")

# Variable names to never rotate (edit this list; also use --exclude on the CLI).
DEFAULT_EXCLUDE_KEYS: frozenset[str] = frozenset(
    {
        # Issued by your mail provider (e.g. Gmail app password); not random DB-style secrets.
        "EMAIL_PASSWORD",
        # Must match the broker user password wherever RabbitMQ is configured.
        "RABBITMQ_PASSWORD",
        # Clients / ops may rely on a stable value; change deliberately, not in bulk rotation.
        "SECRET_ADMIN_KEY",
        # Uncomment if this env reuses another service’s DB credentials you rotate separately:
        # "PAYMENT_DB_PASS",
        # "CARFAX_DB_PASS",
    }
)


def _alnum_pass(length: int = 22) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _gmail_app_password_style() -> str:
    """16 chars in four groups (letters only), similar to Google app passwords."""
    raw = "".join(secrets.choice(string.ascii_lowercase) for _ in range(16))
    return f"{raw[0:4]} {raw[4:8]} {raw[8:12]} {raw[12:16]}"


def default_rotate(key: str) -> bool:
    if key.endswith("_PASS"):
        return True
    return False


def format_value(new_plain: str, original_line_value_part: str) -> str:
    """Preserve outer quoting style from the original value tail."""
    tail = original_line_value_part.strip()
    if len(tail) >= 2 and tail[0] == tail[-1] == '"':
        escaped = new_plain.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if len(tail) >= 2 and tail[0] == tail[-1] == "'":
        escaped = new_plain.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"
    # Unquoted: avoid spaces/specials — use alnum-only
    safe = "".join(c for c in new_plain if c.isalnum())
    if not safe:
        safe = _alnum_pass(22)
    return safe


def value_for_key(key: str) -> str:
    if key == "EMAIL_PASSWORD":
        return _gmail_app_password_style()
    return _alnum_pass(22)


def process_lines(
    lines: list[str],
    rotate_key,
    dry_run: bool,
) -> tuple[list[str], list[tuple[str, str, str]]]:
    """
    Returns (new_lines, changes) where each change is (key, old_display, new_display).
    old_display is truncated for safety.
    """
    out: list[str] = []
    changes: list[tuple[str, str, str]] = []

    def mask(s: str, max_len: int = 24) -> str:
        s = s.strip()
        if len(s) <= max_len:
            return s[:3] + "…" if len(s) > 3 else s
        return s[:3] + "…" + s[-2:]

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            out.append(line)
            continue

        m = ENV_KEY_RE.match(line.rstrip("\n"))
        if not m:
            out.append(line)
            continue

        key, val_part = m.group(1), m.group(2)
        if not rotate_key(key):
            out.append(line)
            continue

        new_plain = value_for_key(key)
        new_val = format_value(new_plain, val_part)
        new_line = f"{key}={new_val}\n" if line.endswith("\n") else f"{key}={new_val}"

        # Extract old plain-ish for display (strip outer quotes)
        old_disp = val_part.strip()
        if (old_disp.startswith('"') and old_disp.endswith('"')) or (
            old_disp.startswith("'") and old_disp.endswith("'")
        ):
            old_disp = old_disp[1:-1]

        changes.append((key, mask(old_disp), mask(new_plain)))
        if dry_run:
            out.append(line)
        else:
            out.append(new_line)

    return out, changes


def main() -> int:
    p = argparse.ArgumentParser(description="Regenerate password fields in .env")
    p.add_argument(
        "--file",
        "-f",
        type=Path,
        default=Path(".env"),
        help="Path to .env (default: ./.env)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show keys that would change; do not write",
    )
    p.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not write .env.bak.<timestamp> before replacing",
    )
    p.add_argument(
        "--extra",
        action="append",
        default=[],
        metavar="KEY",
        help="Additional variable name to rotate (repeatable)",
    )
    p.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="KEY",
        help="Variable name to skip (repeatable); overrides --extra",
    )
    p.add_argument(
        "--skip-secret-admin",
        action="store_true",
        help="Do not rotate SECRET_ADMIN_KEY",
    )
    args = p.parse_args()
    env_path: Path = args.file.resolve()

    extra = set(args.extra)
    exclude = set(DEFAULT_EXCLUDE_KEYS) | set(args.exclude)

    def rotate_key(key: str) -> bool:
        if key in exclude:
            return False
        if args.skip_secret_admin and key == "SECRET_ADMIN_KEY":
            return False
        if key in extra:
            return True
        return default_rotate(key)

    if not env_path.is_file():
        print(f"error: file not found: {env_path}", file=sys.stderr)
        return 1

    text = env_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    new_lines, changes = process_lines(lines, rotate_key, dry_run=args.dry_run)

    if not changes:
        print("No matching keys found; nothing to do.")
        return 0

    print("Planned rotations:" if args.dry_run else "Rotated:")
    for key, old_m, new_m in changes:
        print(f"  {key}: {old_m} -> {new_m}")

    if args.dry_run:
        print("\nDry run: .env not modified.")
        return 0

    if not args.no_backup:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        bak = env_path.with_name(f"{env_path.name}.bak.{ts}")
        shutil.copy2(env_path, bak)
        print(f"\nBackup: {bak}")

    env_path.write_text("".join(new_lines), encoding="utf-8")
    print(f"Updated: {env_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
