#!/bin/bash
# Quick activation script for the virtual environment

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "Virtual environment activated!"
    echo "Python: $(which python) ($(python --version))"
    echo "To deactivate, run: deactivate"
else
    echo "Error: Virtual environment not found. Run ./uv_setup.sh first."
    exit 1
fi
