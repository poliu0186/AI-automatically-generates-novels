#!/usr/bin/env bash
set -euo pipefail

# Incremental update for existing server deployment.
# Run as root:
#   bash deploy/deploy_update.sh

APP_DIR="${APP_DIR:-/opt/ai-novel}"
APP_USER="${APP_USER:-ai-novel}"
SERVICE_NAME="${SERVICE_NAME:-ai-novel}"
TARGET_REF="${TARGET_REF:-main}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

if [ ! -d "$APP_DIR/.git" ]; then
  echo "Git repository not found at $APP_DIR"
  exit 1
fi

sudo -u "$APP_USER" git -C "$APP_DIR" fetch --all --prune
sudo -u "$APP_USER" git -C "$APP_DIR" checkout "$TARGET_REF"
sudo -u "$APP_USER" git -C "$APP_DIR" reset --hard "origin/$TARGET_REF"

sudo -u "$APP_USER" bash -lc "cd '$APP_DIR' && source .venv/bin/activate && pip install -r requirements.txt"

systemctl daemon-reload
systemctl restart "${SERVICE_NAME}.service"
systemctl status "${SERVICE_NAME}.service" --no-pager || true

echo "Update completed for ref=$TARGET_REF"
