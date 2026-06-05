#!/usr/bin/env bash
# Start the Interview Prep Mapper web app.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "No .venv found. Creating one (Python 3.12 recommended)..."
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r requirements.txt
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
echo "Interview Prep Mapper running at http://${HOST}:${PORT}"
exec ./.venv/bin/python -m uvicorn app.main:app --host "$HOST" --port "$PORT" "$@"
