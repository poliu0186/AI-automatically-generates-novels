#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/ai-novel"
cd "$APP_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

exec gunicorn -c gunicorn.conf.py wsgi:app
