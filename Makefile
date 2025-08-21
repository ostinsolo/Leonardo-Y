.PHONY: install install-dev init start test lint clean

# Installation
install:
	pip install -r requirements.txt
	pip install -e .

install-dev:
	pip install -r requirements.txt
	pip install -e ".[dev]"
	playwright install

install-gpu:
	pip install -r requirements.txt
	pip install -e ".[gpu]"

# Setup
init:
	python -m leonardo.main --init

# Running
start:
	python -m leonardo.main --voice

start-debug:
	python -m leonardo.main --voice --debug

# Development
test:
	pytest tests/ -v

lint:
	black leonardo/ tests/
	mypy leonardo/

# Security
audit:
	pip-audit
	bandit -r leonardo/

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# Docker (future)
build-docker:
	docker build -t leonardo:latest .

run-docker:
	docker run -it --rm leonardo:latest

# Help
help:
	@echo "Available targets:"
	@echo "  install      - Install Leonardo and dependencies"
	@echo "  install-dev  - Install with development dependencies"
	@echo "  install-gpu  - Install with GPU support"
	@echo "  init         - Initialize Leonardo for first run"
	@echo "  start        - Start Leonardo voice assistant"
	@echo "  start-debug  - Start with debug logging"
	@echo "  test         - Run tests"
	@echo "  lint         - Run code formatting and type checking"
	@echo "  audit        - Run security audits"
	@echo "  clean        - Clean temporary files"

