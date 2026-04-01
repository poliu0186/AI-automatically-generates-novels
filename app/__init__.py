import os
import logging
import time
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from flask import Flask, redirect, request, session, url_for
from flask_login import current_user
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy import inspect, text
from werkzeug.middleware.proxy_fix import ProxyFix

from app.extensions import db, login_manager
from app.auth import auth_bp, create_user, get_user_by_username
from app.admin import admin_bp
from app.main import main_bp
from app.ai import api_bp
from app.payment import payment_bp
from app.models import User
from app.secret_resolver import resolve_env_bool, resolve_env_int, resolve_env_value


def setup_logging(app, basedir):
    log_level_name = (app.config.get('LOG_LEVEL') or 'INFO').strip().upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    log_dir = Path(app.config.get('LOG_DIR') or (basedir / 'logs'))
    log_file = app.config.get('LOG_FILE') or 'app.log'
    log_max_bytes = max(int(app.config.get('LOG_MAX_BYTES') or 20 * 1024 * 1024), 1024)
    log_backup_count = max(int(app.config.get('LOG_BACKUP_COUNT') or 10), 1)
    log_to_stdout = bool(app.config.get('LOG_TO_STDOUT', True))

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / log_file

    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    handlers = []

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=log_max_bytes,
        backupCount=log_backup_count,
        encoding='utf-8',
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    file_handler.set_name('ai_novel_file')
    handlers.append(file_handler)

    if log_to_stdout:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(log_level)
        stream_handler.setFormatter(formatter)
        stream_handler.set_name('ai_novel_stream')
        handlers.append(stream_handler)

    root_logger = logging.getLogger()
    for existing in list(root_logger.handlers):
        name = getattr(existing, 'name', '') or ''
        if name.startswith('ai_novel_'):
            root_logger.removeHandler(existing)
            existing.close()

    root_logger.setLevel(log_level)
    for handler in handlers:
        root_logger.addHandler(handler)

    app.logger.handlers = []
    app.logger.propagate = True
    app.logger.setLevel(log_level)

    app.logger.info(
        '日志系统已初始化: level=%s, file=%s, max_bytes=%s, backup_count=%s, stdout=%s',
        logging.getLevelName(log_level),
        str(log_path),
        log_max_bytes,
        log_backup_count,
        log_to_stdout,
    )


def create_app():
    basedir = Path(__file__).resolve().parent.parent
    load_dotenv(basedir / '.env')

    app = Flask(
        __name__,
        template_folder=str(basedir / 'templates'),
        static_folder=str(basedir / 'static'),
        static_url_path='/static'
    )
    app.secret_key = resolve_env_value('SECRET_KEY', 'change-me-to-a-secure-key')
    app.config['ENVIRONMENT'] = resolve_env_value('ENVIRONMENT', 'production')
    app.config['FORCE_HTTPS'] = resolve_env_bool('FORCE_HTTPS', True)
    app.config['TRUST_PROXY'] = resolve_env_bool('TRUST_PROXY', True)
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = resolve_env_value('SESSION_COOKIE_SAMESITE', 'Lax')
    app.config['SESSION_COOKIE_SECURE'] = resolve_env_bool('SESSION_COOKIE_SECURE', True)
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['REMEMBER_COOKIE_SECURE'] = resolve_env_bool('REMEMBER_COOKIE_SECURE', True)
    app.config['X_FRAME_OPTIONS'] = resolve_env_value('X_FRAME_OPTIONS', 'SAMEORIGIN')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = resolve_env_value(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/ai_novels'
    )
    app.config['API_ENDPOINT_1'] = resolve_env_value('API_ENDPOINT_1', 'https://open.bigmodel.cn/api/paas/v4/')
    app.config['API_KEY_1'] = resolve_env_value('API_KEY_1', '')
    app.config['API_ENDPOINT_2'] = resolve_env_value('API_ENDPOINT_2', 'https://open.bigmodel.cn/api/paas/v4/')
    app.config['API_KEY_2'] = resolve_env_value('API_KEY_2', '')
    app.config['COINS_PER_1000_TOKENS'] = resolve_env_value('COINS_PER_1000_TOKENS', '1')
    app.config['COINS_PER_YUAN'] = resolve_env_value('COINS_PER_YUAN', '10')
    app.config['REVIEW_AUDIT_COINS'] = resolve_env_value('REVIEW_AUDIT_COINS', '2')
    app.config['MIN_RECHARGE_AMOUNT_YUAN'] = resolve_env_value('MIN_RECHARGE_AMOUNT_YUAN', '10')
    app.config['DEFAULT_ESTIMATED_OUTPUT_TOKENS'] = resolve_env_value('DEFAULT_ESTIMATED_OUTPUT_TOKENS', '1200')
    app.config['PAYMENT_SUBJECT_PREFIX'] = resolve_env_value('PAYMENT_SUBJECT_PREFIX', '小说创作代币充值')
    app.config['ALIPAY_GATEWAY'] = resolve_env_value('ALIPAY_GATEWAY', 'https://openapi.alipay.com/gateway.do')
    app.config['ALIPAY_APP_ID'] = resolve_env_value('ALIPAY_APP_ID', '')
    app.config['ALIPAY_PRIVATE_KEY'] = resolve_env_value('ALIPAY_PRIVATE_KEY', '')
    app.config['ALIPAY_PUBLIC_KEY'] = resolve_env_value('ALIPAY_PUBLIC_KEY', '')
    app.config['ALIPAY_NOTIFY_URL'] = resolve_env_value('ALIPAY_NOTIFY_URL', '')
    app.config['ALIPAY_RETURN_URL'] = resolve_env_value('ALIPAY_RETURN_URL', '')
    app.config['LOGIN_MAX_ATTEMPTS'] = resolve_env_value('LOGIN_MAX_ATTEMPTS', '5')
    app.config['LOGIN_WINDOW_SECONDS'] = resolve_env_value('LOGIN_WINDOW_SECONDS', '300')
    app.config['LOGIN_LOCKOUT_SECONDS'] = resolve_env_value('LOGIN_LOCKOUT_SECONDS', '900')
    app.config['LOGIN_CAPTCHA_TTL_SECONDS'] = resolve_env_value('LOGIN_CAPTCHA_TTL_SECONDS', '180')
    app.config['RESET_PASSWORD_EXPIRE_SECONDS'] = resolve_env_value('RESET_PASSWORD_EXPIRE_SECONDS', '1800')
    app.config['RESET_PASSWORD_RESEND_COOLDOWN_SECONDS'] = resolve_env_value('RESET_PASSWORD_RESEND_COOLDOWN_SECONDS', '60')
    app.config['MAIL_HOST'] = resolve_env_value('MAIL_HOST', '')
    app.config['MAIL_PORT'] = resolve_env_value('MAIL_PORT', '465')
    app.config['MAIL_USE_TLS'] = resolve_env_bool('MAIL_USE_TLS', False)
    app.config['MAIL_USERNAME'] = resolve_env_value('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = resolve_env_value('MAIL_PASSWORD', '')
    app.config['MAIL_SENDER'] = resolve_env_value('MAIL_SENDER', '')
    app.config['MAIL_TIMEOUT_SECONDS'] = resolve_env_value('MAIL_TIMEOUT_SECONDS', '8')
    app.config['USER_ACTION_LOG_MODE'] = resolve_env_value('USER_ACTION_LOG_MODE', 'key_only')
    app.config['ONLINE_USER_ACTIVE_SECONDS'] = resolve_env_int('ONLINE_USER_ACTIVE_SECONDS', 600)
    app.config['ONLINE_HEARTBEAT_INTERVAL_SECONDS'] = resolve_env_int('ONLINE_HEARTBEAT_INTERVAL_SECONDS', 60)
    app.config['ADMIN_2FA_ENABLED'] = resolve_env_bool('ADMIN_2FA_ENABLED', True)
    app.config['ADMIN_OTP_TTL_SECONDS'] = resolve_env_int('ADMIN_OTP_TTL_SECONDS', 300)
    app.config['ADMIN_OTP_RESEND_COOLDOWN_SECONDS'] = resolve_env_int('ADMIN_OTP_RESEND_COOLDOWN_SECONDS', 60)
    app.config['ADMIN_OTP_LENGTH'] = resolve_env_int('ADMIN_OTP_LENGTH', 6)
    app.config['LOG_LEVEL'] = resolve_env_value('LOG_LEVEL', 'INFO')
    app.config['LOG_DIR'] = resolve_env_value('LOG_DIR', str(basedir / 'logs'))
    app.config['LOG_FILE'] = resolve_env_value('LOG_FILE', 'app.log')
    app.config['LOG_TO_STDOUT'] = resolve_env_bool('LOG_TO_STDOUT', True)
    app.config['LOG_MAX_BYTES'] = resolve_env_int('LOG_MAX_BYTES', 20971520)
    app.config['LOG_BACKUP_COUNT'] = resolve_env_int('LOG_BACKUP_COUNT', 10)

    setup_logging(app, basedir)

    if app.config['TRUST_PROXY']:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.session_protection = 'strong'

    @login_manager.unauthorized_handler
    def _handle_unauthorized():
        next_url = request.url if request.method == 'GET' else request.referrer
        endpoint = request.endpoint or ''
        is_admin_route = endpoint.startswith('admin.') or request.path.startswith('/admin/')
        if is_admin_route:
            return redirect(url_for('auth.admin_login', next=next_url))
        return redirect(url_for('auth.login', next=next_url))

    @app.before_request
    def _enforce_https():
        if not app.config.get('FORCE_HTTPS', True):
            return
        if request.is_secure:
            return

        forwarded_proto = (request.headers.get('X-Forwarded-Proto') or '').split(',')[0].strip().lower()
        if forwarded_proto == 'https':
            return

        host = (request.host or '').split(':')[0].lower()
        if host in ('localhost', '127.0.0.1'):
            return

        target = request.url.replace('http://', 'https://', 1)
        return redirect(target, code=301)

    @app.after_request
    def _set_security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        frame_options = (app.config.get('X_FRAME_OPTIONS') or '').strip()
        if frame_options and frame_options.lower() != 'off':
            response.headers.setdefault('X-Frame-Options', frame_options)
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        if request.is_secure:
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload')
        return response

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(payment_bp)

    @app.before_request
    def _touch_user_last_seen():
        if not current_user.is_authenticated:
            return

        endpoint = request.endpoint or ''
        if endpoint.startswith('static'):
            return

        now_ts = int(time.time())
        interval = max(int(app.config.get('ONLINE_HEARTBEAT_INTERVAL_SECONDS', 60) or 60), 10)
        last_touch_ts = int(session.get('_online_last_touch_ts') or 0)
        if now_ts - last_touch_ts < interval:
            return

        previous_seen_ts = int(session.get('_online_last_seen_ts') or 0)
        delta_seconds = max(now_ts - previous_seen_ts, 0)
        cap_seconds = max(int(app.config.get('ONLINE_USER_ACTIVE_SECONDS', 600) or 600), interval)
        counted_seconds = min(delta_seconds, cap_seconds) if previous_seen_ts else 0

        user = User.query.filter_by(id=current_user.id).first()
        if not user:
            return
        user.last_seen_at = datetime.utcnow()
        if counted_seconds > 0:
            user.total_online_seconds = int(user.total_online_seconds or 0) + counted_seconds
        db.session.commit()
        session['_online_last_touch_ts'] = now_ts
        session['_online_last_seen_ts'] = now_ts

    def ensure_auth_schema_updates():
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())

        if 'users' in tables:
            user_columns = {col['name'] for col in inspector.get_columns('users')}
            if 'email' not in user_columns:
                try:
                    with db.engine.begin() as conn:
                        conn.execute(text('ALTER TABLE users ADD COLUMN email VARCHAR(255)'))
                        conn.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)'))
                except Exception:
                    app.logger.exception('Failed to patch users.email column automatically')
            if 'failed_login_attempts' not in user_columns:
                try:
                    with db.engine.begin() as conn:
                        conn.execute(text('ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0 NOT NULL'))
                except Exception:
                    app.logger.exception('Failed to patch users.failed_login_attempts column automatically')
            if 'locked_until' not in user_columns:
                try:
                    with db.engine.begin() as conn:
                        conn.execute(text('ALTER TABLE users ADD COLUMN locked_until TIMESTAMP NULL'))
                except Exception:
                    app.logger.exception('Failed to patch users.locked_until column automatically')
            if 'last_seen_at' not in user_columns:
                try:
                    with db.engine.begin() as conn:
                        conn.execute(text('ALTER TABLE users ADD COLUMN last_seen_at TIMESTAMP NULL'))
                        conn.execute(text('CREATE INDEX IF NOT EXISTS ix_users_last_seen_at ON users (last_seen_at)'))
                except Exception:
                    app.logger.exception('Failed to patch users.last_seen_at column automatically')
            if 'login_count' not in user_columns:
                try:
                    with db.engine.begin() as conn:
                        conn.execute(text('ALTER TABLE users ADD COLUMN login_count INTEGER DEFAULT 0 NOT NULL'))
                except Exception:
                    app.logger.exception('Failed to patch users.login_count column automatically')
            if 'total_online_seconds' not in user_columns:
                try:
                    with db.engine.begin() as conn:
                        conn.execute(text('ALTER TABLE users ADD COLUMN total_online_seconds BIGINT DEFAULT 0 NOT NULL'))
                except Exception:
                    app.logger.exception('Failed to patch users.total_online_seconds column automatically')

    with app.app_context():
        db.create_all()
        ensure_auth_schema_updates()
        admin_username = os.environ.get('ADMIN_USERNAME')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        if admin_username and admin_password and not get_user_by_username(admin_username):
            create_user(admin_username, admin_password, is_admin=True)

    return app
