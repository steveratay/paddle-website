#!/bin/bash

# Exit on any error
set -e

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Running results fetcher..."
python3 results_fetcher.py

echo "Deactivating virtual environment..."
deactivate

echo "Done! Results have been written to docs/results.html"