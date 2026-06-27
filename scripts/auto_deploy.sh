#!/bin/bash
# Sync git branch for this machine's Infisical env and redeploy via Makefile.
set -euo pipefail

MACHINE_ENV_FILE="${MACHINE_ENV_FILE:-/etc/infisical/machine.env}"
if [ ! -f "$MACHINE_ENV_FILE" ]; then
  echo "Missing $MACHINE_ENV_FILE — copy scripts/machine.env.example and fill in Infisical machine identity." >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$MACHINE_ENV_FILE"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

: "${INFISICAL_SECRET_ENV:?INFISICAL_SECRET_ENV must be set in $MACHINE_ENV_FILE}"
: "${INFISICAL_DOMAIN:?INFISICAL_DOMAIN must be set in $MACHINE_ENV_FILE}"
: "${INFISICAL_MACHINE_CLIENT_ID:?INFISICAL_MACHINE_CLIENT_ID must be set in $MACHINE_ENV_FILE}"
: "${INFISICAL_MACHINE_CLIENT_SECRET:?INFISICAL_MACHINE_CLIENT_SECRET must be set in $MACHINE_ENV_FILE}"
: "${INFISICAL_PROJECT_ID:?INFISICAL_PROJECT_ID must be set in $MACHINE_ENV_FILE}"

case "$INFISICAL_SECRET_ENV" in
  staging)
    DEPLOY_BRANCH=demo
    MAKE_GOALS=(deploy demo)
    ;;
  prod)
    DEPLOY_BRANCH=main
    MAKE_GOALS=(deploy prod)
    ;;
  *)
    echo "Unsupported INFISICAL_SECRET_ENV: $INFISICAL_SECRET_ENV (use staging or prod)" >&2
    exit 1
    ;;
esac

command -v infisical >/dev/null 2>&1 || {
  echo "infisical CLI not found on PATH" >&2
  exit 1
}

export INFISICAL_TOKEN INFISICAL_PROJECT_ID INFISICAL_SECRET_ENV INFISICAL_DOMAIN
INFISICAL_TOKEN=$(
  infisical login \
    --method=universal-auth \
    --client-id="$INFISICAL_MACHINE_CLIENT_ID" \
    --client-secret="$INFISICAL_MACHINE_CLIENT_SECRET" \
    --domain="$INFISICAL_DOMAIN" \
    --silent \
    --plain
)
if [ -z "$INFISICAL_TOKEN" ]; then
  echo "Infisical login failed or returned empty token" >&2
  exit 2
fi

git fetch origin "$DEPLOY_BRANCH"
git reset --hard "origin/$DEPLOY_BRANCH"
git clean -fd

make "${MAKE_GOALS[@]}"

echo "Deployment completed successfully ($INFISICAL_SECRET_ENV → origin/$DEPLOY_BRANCH)!"
