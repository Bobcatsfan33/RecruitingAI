# Workforce Intelligence Platform — Makefile
#
# Common dev/test/deploy verbs. Run `make help` for the catalogue.

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

DC := docker compose -f infrastructure/docker/docker-compose.yml

.PHONY: help bootstrap install infra-up infra-down test test-py test-ts \
        lint lint-py lint-ts typecheck migrate seed dev clean

help:
	@awk 'BEGIN {FS = ":.*##"; printf "Targets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

bootstrap: install infra-up migrate ## install deps + bring up infra + run migrations
	@echo "✓ bootstrap complete"

install: ## install all node + python deps
	pnpm install
	uv sync

infra-up: ## start postgres + clickhouse + redis + temporal + minio + opa + mailpit
	$(DC) up -d

infra-down: ## stop infra (keeps volumes)
	$(DC) down

infra-reset: ## stop infra and DELETE volumes (data loss)
	$(DC) down -v

migrate: ## run all migrations (PG + ClickHouse)
	uv run python -m infrastructure.migrations.run_all

seed: ## load synthetic seed data
	uv run python -m infrastructure.seeds.run_all

test: test-py test-ts ## run all tests

test-py: ## run python test suites
	uv run pytest

test-ts: ## run typescript test suites
	pnpm -r --if-present test

lint: lint-py lint-ts ## lint all sources

lint-py:
	uv run ruff check .

lint-ts:
	pnpm -r --if-present lint

typecheck:
	pnpm -r --if-present typecheck
	uv run mypy services packages || true

dev: ## start every service in dev mode (requires overmind or foreman)
	@command -v overmind >/dev/null 2>&1 && overmind start || \
	  (echo "overmind not installed; falling back to foreman"; foreman start)

clean: ## delete build artefacts + caches
	rm -rf node_modules .pnpm-store
	find . -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".ruff_cache" -o -name ".mypy_cache" \) -prune -exec rm -rf {} +
	find . -type d \( -name "dist" -o -name "build" -o -name ".next" \) -prune -exec rm -rf {} +
