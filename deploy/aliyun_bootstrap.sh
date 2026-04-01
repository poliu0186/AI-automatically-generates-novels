#!/usr/bin/env bash
set -euo pipefail

# First-time deployment bootstrap for Aliyun ECS.
# Run as root on server:
#   bash deploy/aliyun_bootstrap.sh https://github.com/<owner>/<repo>.git your-domain.com

REPO_URL="${1:-}"
DOMAIN="${2:-_}"
APP_USER="${APP_USER:-ai-novel}"
APP_DIR="${APP_DIR:-/opt/ai-novel}"
SERVICE_NAME="${SERVICE_NAME:-ai-novel}"

if [ -z "$REPO_URL" ]; then
  echo "Usage: bash deploy/aliyun_bootstrap.sh <repo_url> [domain]"
  exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

install_dependencies() {
  if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y \
      git nginx curl \
      python3 python3-venv python3-pip \
      build-essential libpq-dev
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y \
      git nginx curl \
      python3 python3-pip python3-devel \
      gcc gcc-c++ make postgresql-devel
  elif command -v yum >/dev/null 2>&1; then
    yum install -y epel-release
    yum install -y \
      git nginx curl \
      python3 python3-pip python3-devel \
      gcc gcc-c++ make postgresql-devel
  else
    echo "Unsupported package manager. Install dependencies manually."
    exit 1
  fi
}

ensure_app_user() {
  if ! id -u "$APP_USER" >/dev/null 2>&1; then
    useradd --system --create-home --shell /bin/bash "$APP_USER"
  fi
}

prepare_code() {
  mkdir -p "$APP_DIR"
  chown -R "$APP_USER:$APP_USER" "$APP_DIR"

  if [ -d "$APP_DIR/.git" ]; then
    sudo -u "$APP_USER" git -C "$APP_DIR" fetch --all --prune
    sudo -u "$APP_USER" git -C "$APP_DIR" reset --hard origin/main
  else
    rm -rf "$APP_DIR"
    sudo -u "$APP_USER" git clone "$REPO_URL" "$APP_DIR"
  fi
}

prepare_python_env() {
  sudo -u "$APP_USER" bash -lc "cd '$APP_DIR' && python3 -m venv .venv"
  sudo -u "$APP_USER" bash -lc "cd '$APP_DIR' && source .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
}

prepare_env_file() {
  if [ ! -f "$APP_DIR/.env" ]; then
    if [ -f "$APP_DIR/.env.example" ]; then
      cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    else
      cat > "$APP_DIR/.env" <<'EOF'
SECRET_KEY=change-me
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/ai_novels
ENVIRONMENT=production
FORCE_HTTPS=1
TRUST_PROXY=1
SESSION_COOKIE_SECURE=1
REMEMBER_COOKIE_SECURE=1
ADMIN_2FA_ENABLED=1
LOG_LEVEL=INFO
LOG_DIR=logs
LOG_FILE=app.log
LOG_TO_STDOUT=1
LOG_MAX_BYTES=20971520
LOG_BACKUP_COUNT=10
EOF
    fi
    chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    echo "Created $APP_DIR/.env. Please edit it before going live."
  fi

  mkdir -p "$APP_DIR/logs"
  chown -R "$APP_USER:$APP_USER" "$APP_DIR/logs"
}

install_systemd_service() {
  cp "$APP_DIR/deploy/ai-novel.service" "/etc/systemd/system/${SERVICE_NAME}.service"
  systemctl daemon-reload
  systemctl enable "${SERVICE_NAME}.service"
}

install_nginx_conf() {
  cp "$APP_DIR/deploy/nginx-ai-novel.conf" "/etc/nginx/conf.d/${SERVICE_NAME}.conf"

  if [ "$DOMAIN" != "_" ]; then
    sed -i "s/server_name _;/server_name ${DOMAIN};/g" "/etc/nginx/conf.d/${SERVICE_NAME}.conf"
    sed -i "s|/etc/letsencrypt/live/your-domain/fullchain.pem|/etc/letsencrypt/live/${DOMAIN}/fullchain.pem|g" "/etc/nginx/conf.d/${SERVICE_NAME}.conf"
    sed -i "s|/etc/letsencrypt/live/your-domain/privkey.pem|/etc/letsencrypt/live/${DOMAIN}/privkey.pem|g" "/etc/nginx/conf.d/${SERVICE_NAME}.conf"
  fi

  nginx -t
  systemctl enable nginx
  systemctl restart nginx
}

install_dependencies
ensure_app_user
prepare_code
prepare_python_env
prepare_env_file
install_systemd_service
install_nginx_conf

systemctl restart "${SERVICE_NAME}.service"
systemctl status "${SERVICE_NAME}.service" --no-pager || true

echo "Bootstrap completed."
echo "Next steps:"
echo "1) Edit ${APP_DIR}/.env with real secrets"
echo "2) Configure certificate: certbot --nginx -d ${DOMAIN}"
echo "3) Restart services: systemctl restart ${SERVICE_NAME} nginx"
