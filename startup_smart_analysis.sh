#!/bin/bash

# Daily Smart Analysis Startup Script
# This script runs the Smart Analysis once per day at system startup
# DISABLED TO CONSERVE TRIAL API CALLS

# Set the project directory
PROJECT_DIR="/Users/davidmccarthy/Development/CursorAI/Django/aiadvisor"
VENV_PATH="/Users/davidmccarthy/Development/scratch/python/tutorial-env"

# DISABLED - Smart Analysis is disabled to conserve trial API calls
echo "Smart Analysis is DISABLED to conserve trial API calls."
echo "To enable: uncomment the lines below and comment out this message."

# Change to project directory
# cd "$PROJECT_DIR"

# Activate virtual environment
# source "$VENV_PATH/bin/activate"

# Run the daily smart analysis
# echo "Starting Daily Smart Analysis..."
# python run_daily_smart_analysis.py

# Deactivate virtual environment
# deactivate

# echo "Daily Smart Analysis completed."
