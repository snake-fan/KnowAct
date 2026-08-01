SHELL := /bin/sh

.DEFAULT_GOAL := help

ENV_FILE := .env
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8000
FRONTEND_HOST ?= 127.0.0.1
FRONTEND_PORT ?= 5173
SIMULATOR_TEST_FRONTEND_HOST ?= 127.0.0.1
SIMULATOR_TEST_FRONTEND_PORT ?= 5174
VITE_API_PROXY_TARGET ?= http://$(BACKEND_HOST):$(BACKEND_PORT)
BACKEND_RELOAD ?= 1

ifneq ($(filter 1 true yes,$(BACKEND_RELOAD)),)
BACKEND_RELOAD_FLAG := --reload
endif

.PHONY: help config env setup install backend-install frontend-install \
	simulator-test-frontend-install dev simulator-test backend frontend \
	simulator-test-frontend test build frontend-build \
	simulator-test-frontend-build check

help:
	@printf '%s\n' \
		'KnowAct development commands' \
		'' \
		'  make setup       Create .env when missing and install all dependencies' \
		'  make dev         Start backend and internal research workbench' \
		'  make simulator-test  Start backend and standalone participant app' \
		'  make backend     Start the FastAPI backend' \
		'  make frontend    Start the React/Vite frontend' \
		'  make simulator-test-frontend  Start the standalone participant app' \
		'  make config      Show non-secret startup configuration' \
		'  make env         Create .env from .env.example when missing' \
		'  make install     Install backend and frontend dependencies' \
		'  make test        Run the Python unittest suite' \
		'  make build       Build both React frontends for production' \
		'  make simulator-test-frontend-build  Build only the participant app' \
		'  make check       Run tests and the frontend production build' \
		'' \
		'Override example:' \
		'  make dev BACKEND_PORT=8001 FRONTEND_PORT=5174'

config:
	@printf '%s\n' \
		"Environment file: $(ENV_FILE)" \
		"Backend:         http://$(BACKEND_HOST):$(BACKEND_PORT)" \
		"Frontend:        http://$(FRONTEND_HOST):$(FRONTEND_PORT)" \
		"Simulator Test: http://$(SIMULATOR_TEST_FRONTEND_HOST):$(SIMULATOR_TEST_FRONTEND_PORT)" \
		"Frontend proxy:  $(VITE_API_PROXY_TARGET)" \
		"Backend reload:  $(BACKEND_RELOAD)"
	@if [ -f "$(ENV_FILE)" ]; then \
		printf '%s\n' 'Environment status: present'; \
	else \
		printf '%s\n' 'Environment status: missing (run make env)'; \
	fi

env:
	@if [ -f "$(ENV_FILE)" ]; then \
		printf '%s\n' "Keeping existing $(ENV_FILE)"; \
	else \
		cp .env.example "$(ENV_FILE)"; \
		printf '%s\n' "Created $(ENV_FILE) from .env.example"; \
	fi

setup: env install

install: backend-install frontend-install simulator-test-frontend-install

backend-install:
	uv sync

frontend-install:
	npm --prefix frontend install

simulator-test-frontend-install:
	npm --prefix simulator-test-frontend install

dev:
	+@$(MAKE) --no-print-directory -j2 backend frontend

simulator-test: env
	+@$(MAKE) --no-print-directory -j2 backend simulator-test-frontend

backend: env
	@printf '%s\n' "Starting backend at http://$(BACKEND_HOST):$(BACKEND_PORT)"
	uv run uvicorn backend.main:app $(BACKEND_RELOAD_FLAG) --host "$(BACKEND_HOST)" --port "$(BACKEND_PORT)"

frontend: env
	@printf '%s\n' "Starting frontend at http://$(FRONTEND_HOST):$(FRONTEND_PORT)"
	@printf '%s\n' "Proxying /api and /health to $(VITE_API_PROXY_TARGET)"
	VITE_API_PROXY_TARGET="$(VITE_API_PROXY_TARGET)" npm --prefix frontend run dev -- --host "$(FRONTEND_HOST)" --port "$(FRONTEND_PORT)"

simulator-test-frontend: env
	@printf '%s\n' "Starting standalone Simulator Test at http://$(SIMULATOR_TEST_FRONTEND_HOST):$(SIMULATOR_TEST_FRONTEND_PORT)"
	@printf '%s\n' "Proxying /api and /health to $(VITE_API_PROXY_TARGET)"
	VITE_API_PROXY_TARGET="$(VITE_API_PROXY_TARGET)" npm --prefix simulator-test-frontend run dev -- --host "$(SIMULATOR_TEST_FRONTEND_HOST)" --port "$(SIMULATOR_TEST_FRONTEND_PORT)"

test:
	uv run python -m unittest

build: frontend-build simulator-test-frontend-build

frontend-build:
	npm --prefix frontend run build

simulator-test-frontend-build:
	npm --prefix simulator-test-frontend run build

check: test build
