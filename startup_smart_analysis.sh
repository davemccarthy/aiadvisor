#!/bin/bash

# Daily Smart Analysis Startup Script
# This script runs the Smart Analysis once per day at system startup

# Set the project directory
PROJECT_DIR="/Users/davidmccarthy/Development/CursorAI/Django/aiadvisor"
VENV_PATH="/Users/davidmccarthy/Development/scratch/python/tutorial-env"

# Change to project directory
cd "$PROJECT_DIR"

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Run the daily smart analysis
echo "Starting Daily Smart Analysis..."
python run_daily_smart_analysis.py

# Deactivate virtual environment
deactivate

echo "Daily Smart Analysis completed."
