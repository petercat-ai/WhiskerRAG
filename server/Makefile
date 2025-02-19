PYTHON = python3
VENV := venv
VENV_BIN := $(VENV)/bin
VENV_ACTIVATE:= $(VENV_BIN)/activate
PIP := $(VENV_BIN)/pip
PYTEST_ARGS = -v

.PHONY: all venv install install-dev clean test run format type-check help

all: venv install

$(VENV):
	@echo "Creating virtual environment..."
	@$(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created."
	@$(PIP) install --upgrade pip

install: $(VENV)
	@echo "Installing production dependencies..."
	@echo $(PIP)
	@$(PIP) install -r requirements.txt
	@if [ -f plugins/requirements.txt ]; then \
		$(PIP) install -r plugins/requirements.txt; \
	fi
	@echo "Installation complete."

dev-install: install
	@echo "Installing development dependencies..."
	@$(PIP) install -r requirements-dev.txt
	@pre-commit install
	@echo "Dev installation complete."

clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

test:
	$(BIN)/pytest $(PYTEST_ARGS) tests

test-cov:
	$(BIN)/pytest $(PYTEST_ARGS) --cov=. tests

run:
	@python main.py

format:
	$(VENV_BIN)/black .
	$(VENV_BIN)/isort .

type-check:
	$(VENV_BIN)/mypy .

update-deps:
	$(VENV_BIN)/pip freeze > requirements.txt

update-dev-deps:
	$(VENV_BIN)/pip freeze > requirements-dev.txt

help:
	@echo "Available targets:"
	@echo "  all            - Create virtual environment and install dependencies"
	@echo "  install        - Install dependencies"
	@echo "  install-dev    - Install development dependencies"
	@echo "  clean          - Clean up generated files"
	@echo "  test           - Run tests"
	@echo "  test-cov       - Run tests with coverage"
	@echo "  run            - Run the application"
	@echo "  format         - Format the code"
	@echo "  type-check     - Run type checks"
	@echo "  update-deps    - Update requirements.txt with current dependencies"
	@echo "  update-dev-deps- Update requirements-dev.txt with current development dependencies"
