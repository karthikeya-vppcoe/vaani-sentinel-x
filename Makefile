.PHONY: help install test test-agents health lint format type-check docker-build docker-run clean setup-dev

# Default target
help:
	@echo "Vaani Sentinel X - Development and Deployment Commands"
	@echo ""
	@echo "Setup Commands:"
	@echo "  install        Install dependencies"
	@echo "  setup-dev      Set up development environment"
	@echo ""
	@echo "Testing Commands:"
	@echo "  health         Run system health check"
	@echo "  test           Run all tests"
	@echo "  test-agents    Test all agents individually"
	@echo ""
	@echo "Code Quality Commands:"
	@echo "  lint           Run linters (flake8)"
	@echo "  format         Format code (black)"
	@echo "  type-check     Run type checking (mypy)"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker-build   Build Docker image"
	@echo "  docker-run     Run with Docker Compose"
	@echo "  docker-dev     Run development environment"
	@echo ""
	@echo "Utility Commands:"
	@echo "  clean          Clean temporary files"
	@echo ""

# Installation and setup
install:
	pip install -r requirements.txt

setup-dev:
	pip install -r requirements.txt
	cp .env.template .env
	@echo "Please edit .env file with your API keys and configuration"

# Testing
health:
	python cli/command_center.py health

test:
	python tests/test_system.py
	python tests/test_agents.py

test-agents:
	python scripts/test_agents.py

# Code quality
lint:
	@command -v flake8 >/dev/null 2>&1 || { echo "Installing flake8..."; pip install flake8; }
	flake8 agents/ cli/ config/ utils/ --max-line-length=88 --exclude=venv/

format:
	@command -v black >/dev/null 2>&1 || { echo "Installing black..."; pip install black; }
	black agents/ cli/ config/ utils/ --line-length=88

type-check:
	@command -v mypy >/dev/null 2>&1 || { echo "Installing mypy..."; pip install mypy; }
	mypy agents/ cli/ config/ utils/ --ignore-missing-imports

# Docker commands
docker-build:
	docker build -t vaani-sentinel-x:latest .

docker-run:
	docker-compose up -d

docker-dev:
	docker-compose -f docker-compose.dev.yml up -d

docker-stop:
	docker-compose down

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage .pytest_cache/

# Full deployment check
deploy-check: health test-agents lint
	@echo ""
	@echo "🚀 Deployment readiness check completed!"
	@echo "If all checks passed, the system is ready for deployment."

# Quick start for development
dev-start: setup-dev health
	@echo ""
	@echo "✓ Development environment ready!"
	@echo "Run 'make test-agents' to verify all agents work correctly."