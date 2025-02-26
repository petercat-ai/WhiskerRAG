PYTHON = python3
VENV := venv
VENV_BIN := $(VENV)/bin
VENV_ACTIVATE:= $(VENV_BIN)/activate
PIP := $(VENV_BIN)/pip
PYTEST_ARGS = -v

.PHONY: all venv install install-dev clean test run format type-check help

$(VENV):
	@echo "Creating virtual environment..."
	@$(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created."
	@$(PIP) install --upgrade pip

setup: install
	@echo "Setting up..."
	@pre-commit install

install: $(VENV)
	@echo "Installing production dependencies..."
	@echo $(PIP)
	@$(PIP) install -r requirements.txt
	@if [ -f plugins/requirements.txt ]; then \
		$(PIP) install -r plugins/requirements.txt; \
	fi
	@echo "Installing development dependencies..."
	@$(PIP) install -r requirements-dev.txt
	@echo "Dev installation complete."
	@echo "Installation complete."

install-plugin: 
	@echo "Installing plugin dependencies..."
	@$(PIP) install -r plugins/requirements.txt
	@pre-commit install
	@echo "Dev installation complete."
	@echo "Installation complete."
	
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
	echo "Formatting code..."
	$(VENV_BIN)/black .
	echo "Formatting imports..."
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
	@echo "  clean          - Clean up generated files"
	@echo "  test           - Run tests"
	@echo "  test-cov       - Run tests with coverage"
	@echo "  run            - Run the application"
	@echo "  format         - Format the code"
	@echo "  type-check     - Run type checks"
	@echo "  update-deps    - Update requirements.txt with current dependencies"
	@echo "  update-dev-deps- Update requirements-dev.txt with current development dependencies"
