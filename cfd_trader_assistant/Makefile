# CFD Trader Assistant Makefile
.PHONY: help venv install test run dashboard clean lint format

# Default target
help:
	@echo "CFD Trader Assistant - Available commands:"
	@echo "  venv        - Create virtual environment"
	@echo "  install     - Install dependencies"
	@echo "  test        - Run tests"
	@echo "  run         - Run scanner in intraday mode"
	@echo "  dashboard   - Run Streamlit dashboard"
	@echo "  backtest    - Run backtest"
	@echo "  clean       - Clean temporary files"
	@echo "  lint        - Run linting"
	@echo "  format      - Format code"

# Virtual environment
venv:
	python3.11 -m venv venv
	@echo "Virtual environment created. Activate with: source venv/bin/activate"

# Install dependencies
install:
	pip install --upgrade pip
	pip install -r requirements.txt
	@echo "Dependencies installed"

# Run tests
test:
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

# Run scanner
run:
	python main.py scan --mode intraday

# Run dashboard
dashboard:
	streamlit run app/dashboard.py --server.port 8501 --server.address 0.0.0.0

# Run backtest
backtest:
	python main.py backtest --preset eod_spy_qqq

# Clean temporary files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf data/cache/*
	@echo "Cleaned temporary files"

# Lint code
lint:
	mypy app/
	flake8 app/ tests/
	@echo "Linting completed"

# Format code
format:
	black app/ tests/
	isort app/ tests/
	@echo "Code formatted"

# Docker commands
docker-build:
	docker build -t cfd-trader-assistant .

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

# Development setup
dev-setup: venv install
	@echo "Development environment setup complete"
	@echo "Activate virtual environment: source venv/bin/activate"
	@echo "Copy .env.example to .env and configure your settings"

# Full test suite
test-full: lint test
	@echo "Full test suite completed"

# Production deployment
deploy: clean docker-build
	@echo "Production build ready"