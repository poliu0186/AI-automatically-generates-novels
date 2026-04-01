from flask_login import UserMixin

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime)
    last_seen_at = db.Column(db.DateTime, index=True)
    login_count = db.Column(db.Integer, nullable=False, default=0)
    total_online_seconds = db.Column(db.BigInteger, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    wallet_account = db.relationship('WalletAccount', back_populates='user', uselist=False, cascade='all, delete-orphan')
    recharge_orders = db.relationship('RechargeOrder', back_populates='user', cascade='all, delete-orphan')
    wallet_ledgers = db.relationship('WalletLedger', back_populates='user', cascade='all, delete-orphan')
    llm_usage_records = db.relationship('LLMUsageRecord', back_populates='user', cascade='all, delete-orphan')
    exported_articles = db.relationship('ExportedArticle', back_populates='user', cascade='all, delete-orphan')
    password_reset_requests = db.relationship('PasswordResetRequest', back_populates='user', cascade='all, delete-orphan')
    admin_permissions = db.relationship(
        'SystemUserPermission',
        back_populates='user',
        foreign_keys='SystemUserPermission.user_id',
        uselist=False,
        cascade='all, delete-orphan'
    )
    user_action_logs = db.relationship('UserActionLog', back_populates='user', cascade='all, delete-orphan')

    def get_id(self):
        return str(self.id)


class WalletAccount(db.Model):
    __tablename__ = 'wallet_accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False, index=True)
    available_coins = db.Column(db.BigInteger, nullable=False, default=0)
    reserved_coins = db.Column(db.BigInteger, nullable=False, default=0)
    total_recharged_coins = db.Column(db.BigInteger, nullable=False, default=0)
    total_consumed_coins = db.Column(db.BigInteger, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    user = db.relationship('User', back_populates='wallet_account')
    ledgers = db.relationship('WalletLedger', back_populates='wallet_account', cascade='all, delete-orphan')


class PasswordResetRequest(db.Model):
    __tablename__ = 'password_reset_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    token_hash = db.Column(db.String(128), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    user = db.relationship('User', back_populates='password_reset_requests')


class RechargeOrder(db.Model):
    __tablename__ = 'recharge_orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    order_no = db.Column(db.String(64), unique=True, nullable=False, index=True)
    alipay_trade_no = db.Column(db.String(64), unique=True)
    channel = db.Column(db.String(32), nullable=False, default='alipay')
    amount_yuan = db.Column(db.Numeric(10, 2), nullable=False)
    coins = db.Column(db.BigInteger, nullable=False)
    status = db.Column(db.String(24), nullable=False, default='pending', index=True)
    subject = db.Column(db.String(128), nullable=False)
    buyer_logon_id = db.Column(db.String(128))
    notify_payload = db.Column(db.Text)
    paid_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    user = db.relationship('User', back_populates='recharge_orders')


class LLMUsageRecord(db.Model):
    __tablename__ = 'llm_usage_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    request_id = db.Column(db.String(64), nullable=False, index=True)
    call_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    endpoint = db.Column(db.String(32), nullable=False)
    provider = db.Column(db.String(64), nullable=False)
    model = db.Column(db.String(128), nullable=False)
    estimated_tokens = db.Column(db.Integer, nullable=False, default=0)
    prompt_tokens = db.Column(db.Integer, nullable=False, default=0)
    completion_tokens = db.Column(db.Integer, nullable=False, default=0)
    total_tokens = db.Column(db.Integer, nullable=False, default=0)
    coins_reserved = db.Column(db.BigInteger, nullable=False, default=0)
    coins_charged = db.Column(db.BigInteger, nullable=False, default=0)
    usage_source = db.Column(db.String(24), nullable=False, default='estimated')
    status = db.Column(db.String(24), nullable=False, default='reserved', index=True)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    finished_at = db.Column(db.DateTime)

    user = db.relationship('User', back_populates='llm_usage_records')
    ledgers = db.relationship('WalletLedger', back_populates='usage_record')


class WalletLedger(db.Model):
    __tablename__ = 'wallet_ledgers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    wallet_account_id = db.Column(db.Integer, db.ForeignKey('wallet_accounts.id'), nullable=False, index=True)
    related_usage_id = db.Column(db.Integer, db.ForeignKey('llm_usage_records.id'), index=True)
    change_type = db.Column(db.String(32), nullable=False, index=True)
    available_delta = db.Column(db.BigInteger, nullable=False, default=0)
    reserved_delta = db.Column(db.BigInteger, nullable=False, default=0)
    available_after = db.Column(db.BigInteger, nullable=False)
    reserved_after = db.Column(db.BigInteger, nullable=False)
    related_order_no = db.Column(db.String(64), index=True)
    idempotency_key = db.Column(db.String(128), unique=True)
    remark = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    user = db.relationship('User', back_populates='wallet_ledgers')
    wallet_account = db.relationship('WalletAccount', back_populates='ledgers')
    usage_record = db.relationship('LLMUsageRecord', back_populates='ledgers')


class ExportedArticle(db.Model):
    __tablename__ = 'exported_articles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    format_type = db.Column(db.String(16), nullable=False, default='txt')
    content = db.Column(db.Text, nullable=False)
    content_length = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False, index=True)

    user = db.relationship('User', back_populates='exported_articles')


class AdminSetting(db.Model):
    __tablename__ = 'admin_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False, default='')
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)


class SystemUserPermission(db.Model):
    __tablename__ = 'system_user_permissions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False, index=True)
    can_manage_users = db.Column(db.Boolean, nullable=False, default=True)
    can_manage_pricing = db.Column(db.Boolean, nullable=False, default=True)
    can_manage_wallet_ops = db.Column(db.Boolean, nullable=False, default=True)
    can_view_orders = db.Column(db.Boolean, nullable=False, default=True)
    can_view_logs = db.Column(db.Boolean, nullable=False, default=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    user = db.relationship('User', back_populates='admin_permissions', foreign_keys=[user_id])


class AdminOperationLog(db.Model):
    __tablename__ = 'admin_operation_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    module = db.Column(db.String(64), nullable=False, default='admin')
    action = db.Column(db.String(64), nullable=False)
    detail = db.Column(db.Text)
    ip = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False, index=True)

    admin_user = db.relationship('User', foreign_keys=[admin_user_id])
    target_user = db.relationship('User', foreign_keys=[target_user_id])


class UserActionLog(db.Model):
    __tablename__ = 'user_action_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    action = db.Column(db.String(64), nullable=False)
    detail = db.Column(db.Text)
    ip = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False, index=True)

    user = db.relationship('User', back_populates='user_action_logs')
