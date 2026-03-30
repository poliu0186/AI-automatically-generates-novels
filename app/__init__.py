import os
import logging
from pathlib import Path
from flask import Flask
from openai import OpenAI
from dotenv import load_dotenv

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
    app.config['MIN_RECHARGE_AMOUNT_YUAN'] = os.environ.get('MIN_RECHARGE_AMOUNT_YUAN', '10')
    app.config['DEFAULT_ESTIMATED_OUTPUT_TOKENS'] = os.environ.get('DEFAULT_ESTIMATED_OUTPUT_TOKENS', '1200')
    app.config['PAYMENT_SUBJECT_PREFIX'] = os.environ.get('PAYMENT_SUBJECT_PREFIX', '小说创作代币充值')
    app.config['ALIPAY_GATEWAY'] = os.environ.get('ALIPAY_GATEWAY', 'https://openapi.alipay.com/gateway.do')
    app.config['ALIPAY_APP_ID'] = os.environ.get('ALIPAY_APP_ID', '')
    app.config['ALIPAY_PRIVATE_KEY'] = os.environ.get('ALIPAY_PRIVATE_KEY', '')
    app.config['ALIPAY_PUBLIC_KEY'] = os.environ.get('ALIPAY_PUBLIC_KEY', '')
    app.config['ALIPAY_NOTIFY_URL'] = os.environ.get('ALIPAY_NOTIFY_URL', '')
    app.config['ALIPAY_RETURN_URL'] = os.environ.get('ALIPAY_RETURN_URL', '')

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

    with app.app_context():
        db.create_all()
        admin_username = os.environ.get('ADMIN_USERNAME')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        if admin_username and admin_password and not get_user_by_username(admin_username):
            create_user(admin_username, admin_password, is_admin=True)

    return app
