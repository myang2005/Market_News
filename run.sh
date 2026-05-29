#!/bin/bash
# Start the Market News Dashboard
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Create .env from example if missing
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example — add your API keys there."
fi

PYTHON=/usr/bin/python3
STREAMLIT="$HOME/Library/Python/3.9/bin/streamlit"

echo "Starting Market News Dashboard..."
"$STREAMLIT" run app.py --server.port 8501 --server.headless false
