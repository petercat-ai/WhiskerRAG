#!/bin/bash

# Navigate to the server directory
cd server
poetry install
# Run the petry run dev command
poetry run start