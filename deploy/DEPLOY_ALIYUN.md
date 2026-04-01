# Aliyun ECS Deployment Guide

This guide is for deploying this project to an Aliyun ECS Linux server.

## 1. Prerequisites

- ECS instance with public IP
- Security group allows inbound ports: `22`, `80`, `443`
- Domain DNS A record points to ECS public IP
- Optional but recommended: managed PostgreSQL (RDS)

## 2. First-time Deployment (One Command)

Log in to server and run:

```bash
sudo -i
cd /tmp
git clone https://github.com/poliu0186/AI-automatically-generates-novels.git
cd AI-automatically-generates-novels
bash deploy/aliyun_bootstrap.sh https://github.com/poliu0186/AI-automatically-generates-novels.git your-domain.com
```

This script will:

- Install system dependencies (`python3`, `nginx`, build tools, etc.)
- Create app user `ai-novel`
- Deploy code to `/opt/ai-novel`
- Create python virtual environment and install requirements
- Install systemd service `ai-novel.service`
- Install nginx config
- Start app service and nginx

## 3. Configure Environment Variables

Edit:

```bash
vim /opt/ai-novel/.env
```

At minimum, set these correctly:

- `SECRET_KEY`
- `DATABASE_URL`
- `API_ENDPOINT_1` / `API_KEY_1`
- `API_ENDPOINT_2` / `API_KEY_2`
- `ALIPAY_*`
- `MAIL_*`
- `ENVIRONMENT=production`
- `FORCE_HTTPS=1`
- `TRUST_PROXY=1`
- `SESSION_COOKIE_SECURE=1`
- `REMEMBER_COOKIE_SECURE=1`

Then restart:

```bash
systemctl restart ai-novel nginx
```

## 4. Configure HTTPS Certificate

Use certbot:

```bash
# Debian/Ubuntu
apt-get install -y certbot python3-certbot-nginx

# CentOS/RHEL (dnf/yum depending on distro)
dnf install -y certbot python3-certbot-nginx || yum install -y certbot python3-certbot-nginx

certbot --nginx -d your-domain.com
```

Verify auto-renew:

```bash
systemctl status certbot.timer || true
```

## 5. Service Operations

```bash
systemctl status ai-novel
systemctl restart ai-novel
journalctl -u ai-novel -n 200 --no-pager
```

App logs are also written to:

- `/opt/ai-novel/logs/app.log`

## 6. Daily Update / Release

On server, run:

```bash
cd /opt/ai-novel
bash deploy/deploy_update.sh
```

Or release a branch:

```bash
TARGET_REF=main bash deploy/deploy_update.sh
```

## 7. Security and Health Checks

Run built-in security checklist:

```bash
cd /opt/ai-novel
bash deploy/security-check.sh
```

Quick external verification:

```bash
curl -I http://your-domain.com
curl -I https://your-domain.com
```

Expected:

- HTTP returns `301` redirect to HTTPS
- HTTPS includes security headers

## 8. Rollback (Simple)

If a new release fails:

```bash
cd /opt/ai-novel
sudo -u ai-novel git log --oneline -n 5
sudo -u ai-novel git reset --hard <previous_commit>
systemctl restart ai-novel
```
