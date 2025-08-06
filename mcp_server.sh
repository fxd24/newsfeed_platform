#!/bin/bash

# Newsfeed Platform MCP Server Startup Script
# This script ensures the proper environment is set up for the MCP server

# Change to the project directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..." >&2
    source .venv/bin/activate
else
    echo "Warning: No .venv directory found. Make sure you have the required dependencies installed." >&2
fi

# Set PYTHONPATH to include the current directory so Python can find the src module
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start the MCP server
echo "Starting Newsfeed MCP Server..." >&2
python -m src.mcp_server 