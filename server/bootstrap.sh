#!/bin/bash

# Check if poetry is installed
if ! command -v poetry &> /dev/null
then
  echo "Poetry is not installed, installing..."
  curl -sSL https://install.python-poetry.org | python3 -
  export PATH="$HOME/.local/bin:$PATH"
else
  echo "Poetry is installed"
fi

# Remove lock file
rm -f poetry.lock

# Install dependencies, ignoring lock file
poetry install --no-root

# Activate poetry virtual environment
source $(poetry env info --path)/bin/activate

# Check pip version and force upgrade to the latest
pip install --upgrade pip

# Install dependencies from requirements.txt in ./plugins directory
pip install -r ./plugins/requirements.txt

# Start FastAPI application
uvicorn main:app --host 0.0.0.0 --port 8000