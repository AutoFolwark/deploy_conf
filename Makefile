ENV ?= dev

# e.g. `make up demo` — take env from extra goals; `ENV=...` on the command line wins.
ifneq ($(filter dev demo prod,$(MAKECMDGOALS)),)
ifneq ($(origin ENV),command line)
ENV := $(firstword $(filter dev demo prod,$(MAKECMDGOALS)))
endif
endif

ifeq ($(ENV),dev)
COMPOSE_FILE := dev/docker-compose.dev.yml
INFISICAL_ENV := dev
else ifeq ($(ENV),demo)
COMPOSE_FILE := demo/docker-compose.demo.yml
INFISICAL_ENV := demo
else ifeq ($(ENV),prod)
COMPOSE_FILE := prod/docker-compose.yml
INFISICAL_ENV := prod
else
$(error Unsupported ENV='$(ENV)'. Use dev, demo, or prod)
endif

.PHONY: up down logs restart clean-volumes pull help --env dev demo prod

up: pull
	infisical run --env=$(INFISICAL_ENV) -- docker compose -f $(COMPOSE_FILE) up -d

down:
	docker compose -f $(COMPOSE_FILE) down

logs:
	docker compose -f $(COMPOSE_FILE) logs -f

restart: down up

clean-volumes:
	docker compose -f $(COMPOSE_FILE) down -v

pull:
	docker compose -f $(COMPOSE_FILE) pull

help:
	@echo "Available commands:"
	@echo "  up            - Pull images and start containers"
	@echo "  down          - Stop and remove containers"
	@echo "  logs          - Follow container logs"
	@echo "  restart       - Stop and start containers"
	@echo "  clean-volumes - Stop containers and remove volumes"
	@echo "  pull          - Pull latest images"
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
	@echo "  COMPOSE_FILE  - $(COMPOSE_FILE)"

# No-op targets so `make up <env>` and legacy `make up -- --env <env>` do not fail.
--env dev demo prod:
	@:
