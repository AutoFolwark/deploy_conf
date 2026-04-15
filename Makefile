ENV ?= dev

# e.g. `make up demo` — take env from extra goals; `ENV=...` on the command line wins.
ifneq ($(filter dev demo prod,$(MAKECMDGOALS)),)
ifneq ($(origin ENV),command line)
ENV := $(firstword $(filter dev demo prod,$(MAKECMDGOALS)))
endif
endif

ifeq ($(ENV),dev)
# Merge base + dev overlay; embedded-datastores profile starts bundled Postgres/Redis/RabbitMQ/Adminer.
# Variables (CONTAINER_TAG, POSTGRES_*, …) come from `infisical run` / your shell, not from a repo .env file.
# Keep flags in sync with scripts/initialize_db_users/compose_dev_argv.py
DOCKER_COMPOSE := docker compose --profile embedded-datastores -f general/docker-compose.base.yml -f dev/docker-compose.dev.yml
INFISICAL_ENV := dev
else ifeq ($(ENV),demo)
# Compose/pg_stack_up still use ENV=demo; Infisical secrets load from the "staging" environment.
DOCKER_COMPOSE := docker compose -f demo/docker-compose.demo.yml
INFISICAL_ENV := staging
else ifeq ($(ENV),prod)
DOCKER_COMPOSE := docker compose -f prod/docker-compose.yml
INFISICAL_ENV := prod
else
$(error Unsupported ENV='$(ENV)'. Use dev, demo, or prod)
endif

.PHONY: up down logs restart clean-volumes pull help --env dev demo prod

# `pull` must run under the same env as compose (Infisical / exported vars). A bare `docker compose pull`
# before `infisical run` fails on ${POSTGRES_PASSWORD:?…} and empty DB_* substitutions.
ifeq ($(ENV),prod)
up:
	infisical run --env=$(INFISICAL_ENV) -- sh -c '$(DOCKER_COMPOSE) pull && $(DOCKER_COMPOSE) up -d'
else
up:
	infisical run --env=$(INFISICAL_ENV) -- sh -c '$(DOCKER_COMPOSE) pull && bash ./scripts/pg_stack_up.sh $(ENV)'
endif

down:
	infisical run --env=$(INFISICAL_ENV) -- $(DOCKER_COMPOSE) down

logs:
	infisical run --env=$(INFISICAL_ENV) -- $(DOCKER_COMPOSE) logs -f

restart: down up

clean-volumes:
	infisical run --env=$(INFISICAL_ENV) -- $(DOCKER_COMPOSE) down -v

pull:
	infisical run --env=$(INFISICAL_ENV) -- $(DOCKER_COMPOSE) pull

help:
	@echo "Available commands:"
	@echo "  up            - Pull images and start containers"
	@echo "  down          - Stop and remove containers"
	@echo "  logs          - Follow container logs"
	@echo "  restart       - Stop and start containers"
	@echo "  clean-volumes - Stop containers and remove volumes"
	@echo "  pull          - Pull latest images"
	@echo "  (dev/demo up runs scripts/initialize.py — Postgres + Redis preflight)"
	@echo "  down/logs/clean-volumes/pull run via infisical (demo stack uses Infisical env staging)."
	@echo "  help          - Show this help message"
	@echo ""
	@echo "Environment selection:"
	@echo "  default       - make up                 (uses dev)"
	@echo "  variable      - make up ENV=prod"
	@echo "  extra goal    - make up demo            (or dev / prod)"
	@echo ""
	@echo "Resolved settings:"
	@echo "  ENV           - $(ENV)"
	@echo "  INFISICAL_ENV - $(INFISICAL_ENV)"
	@echo "  DOCKER_COMPOSE - $(DOCKER_COMPOSE)"

# No-op targets so `make up <env>` and legacy `make up -- --env <env>` do not fail.
--env dev demo prod:
	@:
