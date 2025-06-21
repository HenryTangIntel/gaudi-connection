#!/bin/bash

# Initialize UV project
echo "Initializing UV project for gaudi-connection..."

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "UV is not installed. Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Create virtual environment
echo "Creating virtual environment with UV..."
uv venv

# Install dependencies
echo "Installing dependencies..."
uv pip install -e .

# Install development dependencies
echo "Installing development dependencies..."
uv pip install -e ".[dev]"

echo "UV setup complete. Activate the environment with: source .venv/bin/activate"
