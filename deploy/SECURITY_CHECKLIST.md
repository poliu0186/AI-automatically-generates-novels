# Production Security Checklist

## 1. HTTPS and Reverse Proxy

- Ensure domain DNS points to your cloud server.
- Enable TLS certificate (Let's Encrypt recommended).
- Confirm HTTP is redirected to HTTPS.
- Confirm `X-Forwarded-Proto` is passed by Nginx.

## 2. App Environment Variables

Set these values in `.env` for public deployment:

- `ENVIRONMENT=production`
- `FORCE_HTTPS=1`
- `TRUST_PROXY=1`
- `SESSION_COOKIE_SECURE=1`
- `REMEMBER_COOKIE_SECURE=1`
- `ADMIN_2FA_ENABLED=1`
- `ADMIN_OTP_TTL_SECONDS=300`
- `ADMIN_OTP_RESEND_COOLDOWN_SECONDS=60`
- `ADMIN_OTP_LENGTH=6`

## 3. Access and Network

- Only expose ports `80/443` in cloud security group.
- Keep Gunicorn and database bound to internal interface.
- Restrict SSH source IPs if possible.

## 4. Secrets

- Rotate `SECRET_KEY` before production.
- Keep payment keys and model API keys outside git.
- Use least privilege credentials for database users.

## 5. Brute-force and Abuse Protection

- Enable Nginx request rate limiting for login endpoints.
- Monitor failed logins and locked accounts.
- Keep CAPTCHA enabled for login forms.

## 6. Verification Commands

Run local checks:

```bash
bash deploy/security-check.sh
```

Validate HTTPS externally:

```bash
curl -I http://your-domain
curl -I https://your-domain
```

Expected:

- `http://` should return `301` to `https://`.
- `https://` response should include HSTS and other security headers.
