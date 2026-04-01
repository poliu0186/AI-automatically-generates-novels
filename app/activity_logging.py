from flask import current_app, has_request_context, request

from app.extensions import db
from app.models import AdminSetting, User, UserActionLog

USER_ACTION_LOG_MODES = ('all', 'key_only', 'none')
DEFAULT_USER_ACTION_LOG_MODE = 'key_only'
KEY_USER_ACTIONS = {
    'login_success',
    'create_recharge_order',
    'recharge_paid',
    'feature_charge',
    'ai_generate_completed',
    'novel_export_download',
}


def get_user_action_log_mode(default=None):
    fallback = (default or current_app.config.get('USER_ACTION_LOG_MODE', DEFAULT_USER_ACTION_LOG_MODE) or DEFAULT_USER_ACTION_LOG_MODE).strip().lower()
    if fallback not in USER_ACTION_LOG_MODES:
        fallback = DEFAULT_USER_ACTION_LOG_MODE

    row = AdminSetting.query.filter_by(key='user_action_log_mode').first()
    value = (row.value if row and row.value is not None else fallback).strip().lower()
    if value not in USER_ACTION_LOG_MODES:
        return fallback
    return value



def should_log_user_action(action, mode=None):
    current_mode = (mode or get_user_action_log_mode()).strip().lower()
    if current_mode == 'none':
        return False
    if current_mode == 'all':
        return True
    return str(action or '').strip() in KEY_USER_ACTIONS



def client_ip():
    if not has_request_context():
        return ''
    return (request.headers.get('X-Forwarded-For', '').split(',')[0] or request.remote_addr or '').strip()[:64]



def log_user_action(user_id, action, detail=''):
    if not user_id or not should_log_user_action(action):
        return False

    user = User.query.get(int(user_id))
    if not user or bool(getattr(user, 'is_admin', False)):
        return False

    db.session.add(
        UserActionLog(
            user_id=user_id,
            action=str(action or '').strip()[:64],
            detail=(detail or '')[:2000],
            ip=client_ip(),
        )
    )
    return True
