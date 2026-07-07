export DOCKER_BUILDKIT=0

COMPOSE_BASE=docker-compose.yml
COMPOSE_DEV=docker-compose.dev.yml
USE_DEV?=0

ifeq ($(USE_DEV),1)
COMPOSE_FILES=$(COMPOSE_BASE) $(COMPOSE_DEV)
else
COMPOSE_FILES=$(COMPOSE_BASE)
endif

COMPOSE_CMD=docker compose $(foreach file,$(COMPOSE_FILES),-f $(file))

.PHONY: up down reset logs logs-temporal logs-frontend supabase-status

# `up` starts the full local Supabase stack (Postgres + API/Kong + Auth +
# Storage + Studio) via the Supabase CLI, applying migrations and seed, THEN
# brings up Temporal + worker + frontend via docker compose.
up:
	supabase start
	@eval "$$(./scripts/supabase-env.sh)"; $(COMPOSE_CMD) up -d
	@echo ""
	@echo "Stack up. Frontend http://localhost:3000 | Temporal UI http://localhost:8080 | Supabase Studio http://localhost:54323"

down:
	$(COMPOSE_CMD) down
	supabase stop

# Full wipe: tear down compose volumes AND the Supabase stack (incl. its DB),
# then recreate everything from scratch (migrations + seed re-applied).
reset:
	$(COMPOSE_CMD) down -v
	-supabase stop --no-backup
	$(MAKE) up

logs:
	$(COMPOSE_CMD) logs -f

logs-temporal:
	$(COMPOSE_CMD) logs -f temporal temporal-worker

logs-frontend:
	$(COMPOSE_CMD) logs -f frontend

# Supabase is CLI-managed, not a compose service -- use this for its status/keys.
supabase-status:
	supabase status

# Worker and API commands (for local development)
worker:
	cd temporal && python src/worker.py

api:
	cd temporal && python start_api.py

# Start both worker and API together
worker-api:
	cd temporal && python start_all.py

# Testing commands
.PHONY: test-frontend test-backend test-integration test-e2e test-all test-coverage

test-frontend:
	cd frontend && npm run test:unit

test-backend:
	cd temporal && pytest tests/ -m "not integration"

test-integration:
	cd temporal && pytest tests/integration/

test-e2e:
	cd frontend && npx playwright test

test-all:
	$(MAKE) test-frontend
	$(MAKE) test-backend
	@echo ""
	@echo "✅ All unit tests passed"

test-coverage:
	cd frontend && npm run test:unit
	cd temporal && pytest --cov=src --cov-report=html --cov-report=term
	@echo ""
	@echo "Coverage reports generated:"
	@echo "  Frontend: frontend/coverage/index.html"
	@echo "  Backend: temporal/htmlcov/index.html"

# CI simulation (runs all tests including E2E)
ci-test:
	$(MAKE) up
	@sleep 10
	$(MAKE) test-frontend
	$(MAKE) test-backend
	$(MAKE) test-e2e
	$(MAKE) down
	@echo ""
	@echo "✅ Full CI test suite passed"
