#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
NGINX_FILE="${ROOT_DIR}/deploy/nginx-ai-novel.conf"

pass() {
  echo "[PASS] $1"
}

warn() {
  echo "[WARN] $1"
}

check_env_value() {
  local key="$1"
  local expected="$2"
  if grep -E "^${key}=" "$ENV_FILE" >/dev/null 2>&1; then
    local value
    value="$(grep -E "^${key}=" "$ENV_FILE" | tail -n1 | cut -d'=' -f2-)"
    if [ "$value" = "$expected" ]; then
      pass "$key=$expected"
    else
      warn "$key=$value (recommended: $expected)"
    fi
  else
    warn "$key missing (recommended: $expected)"
  fi
}

check_sensitive_key_not_plaintext() {
  local key="$1"
  local value=""
  local has_value=0
  local has_file_ref=0

  if grep -E "^${key}=" "$ENV_FILE" >/dev/null 2>&1; then
    value="$(grep -E "^${key}=" "$ENV_FILE" | tail -n1 | cut -d'=' -f2-)"
    has_value=1
  fi

  if grep -E "^${key}_FILE=" "$ENV_FILE" >/dev/null 2>&1; then
    has_file_ref=1
  fi

  if [ "$has_file_ref" -eq 1 ]; then
    pass "${key}_FILE configured"
    return
  fi

  if [ "$has_value" -eq 0 ] || [ -z "$value" ]; then
    warn "$key missing (recommended: use ${key}_FILE or ENC:... value)"
    return
  fi

  if printf '%s' "$value" | grep -q '^ENC:'; then
    pass "$key uses encrypted value"
  else
    warn "$key appears to be plaintext (recommended: ${key}_FILE or ENC:...)"
  fi
}

echo "Security checklist for AI novel deployment"

echo "1) Environment file checks"
if [ -f "$ENV_FILE" ]; then
  pass ".env exists"
  check_env_value "FORCE_HTTPS" "1"
  check_env_value "TRUST_PROXY" "1"
  check_env_value "SESSION_COOKIE_SECURE" "1"
  check_env_value "REMEMBER_COOKIE_SECURE" "1"
  check_env_value "ADMIN_2FA_ENABLED" "1"
  check_sensitive_key_not_plaintext "SECRET_KEY"
  check_sensitive_key_not_plaintext "API_KEY_1"
  check_sensitive_key_not_plaintext "API_KEY_2"
  check_sensitive_key_not_plaintext "ALIPAY_PRIVATE_KEY"
  check_sensitive_key_not_plaintext "MAIL_PASSWORD"
else
  warn ".env not found at $ENV_FILE"
fi

echo "2) Nginx config checks"
if [ -f "$NGINX_FILE" ]; then
  pass "nginx config exists"
  grep -q "listen 443 ssl" "$NGINX_FILE" && pass "HTTPS listener found" || warn "HTTPS listener missing"
  grep -q "return 301 https://\$host\$request_uri" "$NGINX_FILE" && pass "HTTP->HTTPS redirect found" || warn "HTTP->HTTPS redirect missing"
  grep -q "Strict-Transport-Security" "$NGINX_FILE" && pass "HSTS header configured" || warn "HSTS header missing"
  grep -q "limit_req_zone" "$NGINX_FILE" && pass "rate limit zones configured" || warn "rate limit zones missing"
else
  warn "nginx config not found at $NGINX_FILE"
fi

echo "3) Runtime/network checks"
if command -v ss >/dev/null 2>&1; then
  echo "Open listening ports (ss -ltnp):"
  ss -ltnp || true
else
  warn "ss command not available"
fi

if command -v nginx >/dev/null 2>&1; then
  nginx -t && pass "nginx config syntax ok" || warn "nginx config syntax failed"
else
  warn "nginx not installed in current environment"
fi

echo "Checklist completed"
