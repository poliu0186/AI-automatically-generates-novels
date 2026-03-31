import os
import logging
from pathlib import Path
from flask import Flask
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy import inspect, text

from app.extensions import db, login_manager
from app.auth import auth_bp, create_user, get_user_by_username
from app.admin import admin_bp
from app.main import main_bp
from app.ai import api_bp
from app.payment import payment_bp


def create_app():
    basedir = Path(__file__).resolve().parent.parent
    load_dotenv(basedir / '.env')

    app = Flask(
        __name__,
        template_folder=str(basedir / 'templates'),
        static_folder=str(basedir / 'static'),
        static_url_path='/static'
    )
    app.secret_key = os.environ.get('SECRET_KEY', 'change-me-to-a-secure-key')
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/ai_novels'
    )
    app.config['API_ENDPOINT_1'] = os.environ.get('API_ENDPOINT_1', 'https://open.bigmodel.cn/api/paas/v4/')
    app.config['API_KEY_1'] = os.environ.get('API_KEY_1', '')
    app.config['API_ENDPOINT_2'] = os.environ.get('API_ENDPOINT_2', 'https://open.bigmodel.cn/api/paas/v4/')
    app.config['API_KEY_2'] = os.environ.get('API_KEY_2', '')
    app.config['COINS_PER_1000_TOKENS'] = os.environ.get('COINS_PER_1000_TOKENS', '1')
    app.config['COINS_PER_YUAN'] = os.environ.get('COINS_PER_YUAN', '10')
    app.config['REVIEW_AUDIT_COINS'] = os.environ.get('REVIEW_AUDIT_COINS', '2')
    app.config['MIN_RECHARGE_AMOUNT_YUAN'] = os.environ.get('MIN_RECHARGE_AMOUNT_YUAN', '10')
    app.config['DEFAULT_ESTIMATED_OUTPUT_TOKENS'] = os.environ.get('DEFAULT_ESTIMATED_OUTPUT_TOKENS', '1200')
    app.config['PAYMENT_SUBJECT_PREFIX'] = os.environ.get('PAYMENT_SUBJECT_PREFIX', '小说创作代币充值')
    app.config['ALIPAY_GATEWAY'] = os.environ.get('ALIPAY_GATEWAY', 'https://openapi.alipay.com/gateway.do')
    app.config['ALIPAY_APP_ID'] = os.environ.get('ALIPAY_APP_ID', '')
    app.config['ALIPAY_PRIVATE_KEY'] = os.environ.get('ALIPAY_PRIVATE_KEY', '')
    app.config['ALIPAY_PUBLIC_KEY'] = os.environ.get('ALIPAY_PUBLIC_KEY', '')
    app.config['ALIPAY_NOTIFY_URL'] = os.environ.get('ALIPAY_NOTIFY_URL', '')
    app.config['ALIPAY_RETURN_URL'] = os.environ.get('ALIPAY_RETURN_URL', '')
    app.config['LOGIN_MAX_ATTEMPTS'] = os.environ.get('LOGIN_MAX_ATTEMPTS', '5')
    app.config['LOGIN_WINDOW_SECONDS'] = os.environ.get('LOGIN_WINDOW_SECONDS', '300')
    app.config['LOGIN_LOCKOUT_SECONDS'] = os.environ.get('LOGIN_LOCKOUT_SECONDS', '900')
    app.config['LOGIN_CAPTCHA_TTL_SECONDS'] = os.environ.get('LOGIN_CAPTCHA_TTL_SECONDS', '180')
    app.config['RESET_PASSWORD_EXPIRE_SECONDS'] = os.environ.get('RESET_PASSWORD_EXPIRE_SECONDS', '1800')
    app.config['RESET_PASSWORD_RESEND_COOLDOWN_SECONDS'] = os.environ.get('RESET_PASSWORD_RESEND_COOLDOWN_SECONDS', '60')
    app.config['MAIL_HOST'] = os.environ.get('MAIL_HOST', '')
    app.config['MAIL_PORT'] = os.environ.get('MAIL_PORT', '465')
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', '0') in ('1', 'true', 'True')
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
    app.config['MAIL_SENDER'] = os.environ.get('MAIL_SENDER', '')
    app.config['MAIL_TIMEOUT_SECONDS'] = os.environ.get('MAIL_TIMEOUT_SECONDS', '8')

    logging.basicConfig(level=logging.DEBUG)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.session_protection = 'strong'

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(payment_bp)

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

    with app.app_context():
        db.create_all()
        ensure_auth_schema_updates()
        admin_username = os.environ.get('ADMIN_USERNAME')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        if admin_username and admin_password and not get_user_by_username(admin_username):
            create_user(admin_username, admin_password, is_admin=True)

    return app
