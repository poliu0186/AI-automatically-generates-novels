import json
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.activity_logging import DEFAULT_USER_ACTION_LOG_MODE, USER_ACTION_LOG_MODES
from app.auth import admin_required
from app.billing import InsufficientBalanceError, admin_adjust_wallet
from app.extensions import db
from app.models import AdminSetting, RechargeOrder, SystemUserPermission, User, UserActionLog, WalletLedger

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


PERMISSION_LABELS = {
    'can_manage_users': '用户管理',
    'can_manage_pricing': '费率与活动配置',
    'can_manage_wallet_ops': '代币补发/扣除',
    'can_view_orders': '订单流水查看',
    'can_view_logs': '日志查看',
}

USER_LOG_MODE_LABELS = {
    'all': '全量采集',
    'key_only': '仅关键步骤',
    'none': '关闭采集',
}


def _save_setting(key, value, operator_id):
    row = AdminSetting.query.filter_by(key=key).first()
    if not row:
        row = AdminSetting(key=key)
        db.session.add(row)
    row.value = str(value)
    row.updated_by = operator_id
    return row


def _get_setting(key, default=''):
    row = AdminSetting.query.filter_by(key=key).first()
    if row and row.value is not None:
        return row.value
    return default


def _get_permission_row(user_id):
    row = SystemUserPermission.query.filter_by(user_id=user_id).first()
    if row:
        return row
    row = SystemUserPermission(user_id=user_id)
    db.session.add(row)
    db.session.flush()
    return row


def _safe_page(name, default=1):
    try:
        page = int(request.args.get(name, default))
    except (TypeError, ValueError):
        page = default
    return max(page, 1)


def _paginate_query(query, page, per_page=20):
    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    safe_page = min(max(page, 1), pages)
    items = query.offset((safe_page - 1) * per_page).limit(per_page).all()
    return {
        'items': items,
        'page': safe_page,
        'pages': pages,
        'per_page': per_page,
        'total': total,
    }


def _build_dashboard_url(**changes):
    params = request.args.to_dict(flat=True)
    for key, value in changes.items():
        if value in (None, ''):
            params.pop(key, None)
        else:
            params[key] = value
    return url_for('admin.admin_dashboard', **params)


def _build_dashboard_page_url(page_key, page_value, tab_name):
    return _build_dashboard_url(tab=tab_name, **{page_key: page_value})


def _format_duration(seconds):
    total = max(int(seconds or 0), 0)
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days > 0:
        return f'{days}天{hours}小时{minutes}分钟'
    if hours > 0:
        return f'{hours}小时{minutes}分钟'
    if minutes > 0:
        return f'{minutes}分钟{secs}秒'
    return f'{secs}秒'


def _get_user_log_mode():
    mode = (_get_setting('user_action_log_mode', current_app.config.get('USER_ACTION_LOG_MODE', DEFAULT_USER_ACTION_LOG_MODE)) or DEFAULT_USER_ACTION_LOG_MODE).strip().lower()
    if mode not in USER_ACTION_LOG_MODES:
        return DEFAULT_USER_ACTION_LOG_MODE
    return mode


def _has_permission(code):
    if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
        return False
    row = SystemUserPermission.query.filter_by(user_id=current_user.id).first()
    if not row:
        return True
    return bool(getattr(row, code, True))


@admin_bp.route('/')
@login_required
@admin_required
def admin_dashboard():
    active_tab = request.args.get('tab', 'users')
    tab_permissions = {
        'users': 'can_manage_users',
        'pricing': 'can_manage_pricing',
        'permissions': 'can_manage_users',
        'orders': 'can_view_orders',
        'logs': 'can_view_logs',
    }
    need_permission = tab_permissions.get(active_tab, 'can_manage_users')
    if not _has_permission(need_permission):
        flash('当前账号无权访问该后台模块。', 'danger')
        active_tab = 'users'

    users = User.query.order_by(User.created_at.desc()).all()
    user_permissions = {
        row.user_id: row
        for row in SystemUserPermission.query.filter(SystemUserPermission.user_id.in_([u.id for u in users])).all()
    }

    pricing = {
        'coins_per_1000_tokens': _get_setting('coins_per_1000_tokens', str(current_app.config.get('COINS_PER_1000_TOKENS', '1'))),
        'coins_per_yuan': _get_setting('coins_per_yuan', str(current_app.config.get('COINS_PER_YUAN', '10'))),
        'review_audit_coins': _get_setting('review_audit_coins', str(current_app.config.get('REVIEW_AUDIT_COINS', '2'))),
        'min_recharge_amount_yuan': _get_setting('min_recharge_amount_yuan', str(current_app.config.get('MIN_RECHARGE_AMOUNT_YUAN', '10'))),
        'payment_channel': _get_setting('payment_channel', 'alipay')
    }

    campaign_default = '{\n  "enabled": false,\n  "name": "",\n  "start_at": "",\n  "end_at": "",\n  "bonus_rules": []\n}'
    campaign = _get_setting('recharge_campaign_config', campaign_default)

    online_window_seconds = max(int(current_app.config.get('ONLINE_USER_ACTIVE_SECONDS', 600) or 600), 60)
    online_since = datetime.utcnow() - timedelta(seconds=online_window_seconds)
    online_users = User.query.filter(
        User.is_active.is_(True),
        User.last_seen_at.isnot(None),
        User.last_seen_at >= online_since,
    ).order_by(User.last_seen_at.desc()).all()

    order_query_text = (request.args.get('order_q') or '').strip()
    ledger_query_text = (request.args.get('ledger_q') or '').strip()
    user_log_query_text = (request.args.get('user_log_q') or '').strip()

    orders_query = RechargeOrder.query.outerjoin(User, RechargeOrder.user_id == User.id)
    if order_query_text:
        orders_query = orders_query.filter(or_(
            RechargeOrder.order_no.ilike(f'%{order_query_text}%'),
            RechargeOrder.status.ilike(f'%{order_query_text}%'),
            RechargeOrder.channel.ilike(f'%{order_query_text}%'),
            User.username.ilike(f'%{order_query_text}%')
        ))
    orders_pagination = _paginate_query(orders_query.order_by(RechargeOrder.created_at.desc()), _safe_page('order_page'))

    ledger_query = WalletLedger.query.outerjoin(User, WalletLedger.user_id == User.id)
    if ledger_query_text:
        ledger_query = ledger_query.filter(or_(
            WalletLedger.change_type.ilike(f'%{ledger_query_text}%'),
            WalletLedger.related_order_no.ilike(f'%{ledger_query_text}%'),
            WalletLedger.remark.ilike(f'%{ledger_query_text}%'),
            User.username.ilike(f'%{ledger_query_text}%')
        ))
    ledger_pagination = _paginate_query(ledger_query.order_by(WalletLedger.created_at.desc()), _safe_page('ledger_page'))

    user_logs_query = UserActionLog.query.outerjoin(User, UserActionLog.user_id == User.id)
    if user_log_query_text:
        user_logs_query = user_logs_query.filter(or_(
            UserActionLog.action.ilike(f'%{user_log_query_text}%'),
            UserActionLog.detail.ilike(f'%{user_log_query_text}%'),
            UserActionLog.ip.ilike(f'%{user_log_query_text}%'),
            User.username.ilike(f'%{user_log_query_text}%')
        ))
    user_logs_pagination = _paginate_query(user_logs_query.order_by(UserActionLog.created_at.desc()), _safe_page('user_log_page'))

    return render_template(
        'admin.html',
        users=users,
        user_permissions=user_permissions,
        permission_labels=PERMISSION_LABELS,
        pricing=pricing,
        campaign=campaign,
        order_query_text=order_query_text,
        ledger_query_text=ledger_query_text,
        user_log_query_text=user_log_query_text,
        orders_pagination=orders_pagination,
        ledger_pagination=ledger_pagination,
        user_logs_pagination=user_logs_pagination,
        active_tab=active_tab,
        user_log_mode=_get_user_log_mode(),
        user_log_mode_labels=USER_LOG_MODE_LABELS,
        build_dashboard_url=_build_dashboard_url,
        build_dashboard_page_url=_build_dashboard_page_url,
        online_users=online_users,
        online_user_count=len(online_users),
        online_window_seconds=online_window_seconds,
        format_duration=_format_duration,
    )


@admin_bp.route('/user/<int:user_id>/action', methods=['POST'])
@login_required
@admin_required
def admin_user_action(user_id):
    if not _has_permission('can_manage_users'):
        flash('当前账号没有用户管理权限。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='users'))

    action = request.form.get('action')
    user = User.query.get(user_id)
    if not user:
        flash('用户不存在。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='users'))

    if user.id == current_user.id and action in ('toggle_active', 'toggle_admin'):
        flash('管理员不能修改自身状态。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='users'))

    if action == 'toggle_admin':
        user.is_admin = not user.is_admin
        if user.is_admin:
            _get_permission_row(user.id)
        flash(f'已将用户 {user.username} 的管理员权限设置为 {user.is_admin}。', 'success')
    elif action == 'toggle_active':
        user.is_active = not user.is_active
        flash(f'已将用户 {user.username} 的状态设置为 {"启用" if user.is_active else "禁用"}。', 'success')
    elif action == 'unlock':
        user.failed_login_attempts = 0
        user.locked_until = None
        flash(f'已解锁用户 {user.username}。', 'success')
    else:
        flash('未知操作。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='users'))

    db.session.commit()
    return redirect(url_for('admin.admin_dashboard', tab='users'))


@admin_bp.route('/settings/pricing', methods=['POST'])
@login_required
@admin_required
def admin_update_pricing():
    if not _has_permission('can_manage_pricing'):
        flash('当前账号没有费率配置权限。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='pricing'))

    form = request.form
    try:
        coins_per_1000 = Decimal(str(form.get('coins_per_1000_tokens', '1')))
        coins_per_yuan = Decimal(str(form.get('coins_per_yuan', '10')))
        review_audit = int(form.get('review_audit_coins', '2'))
        min_recharge = Decimal(str(form.get('min_recharge_amount_yuan', '10')))
    except (InvalidOperation, ValueError):
        flash('费率配置格式错误，请检查输入。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='pricing'))

    if coins_per_1000 <= 0 or coins_per_yuan <= 0 or review_audit < 0 or min_recharge <= 0:
        flash('费率配置必须是正数，审核扣费不能为负。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='pricing'))

    payment_channel = (form.get('payment_channel') or 'alipay').strip().lower()
    if payment_channel not in ('alipay', 'manual'):
        payment_channel = 'alipay'

    _save_setting('coins_per_1000_tokens', str(coins_per_1000), current_user.id)
    _save_setting('coins_per_yuan', str(coins_per_yuan), current_user.id)
    _save_setting('review_audit_coins', str(review_audit), current_user.id)
    _save_setting('min_recharge_amount_yuan', str(min_recharge), current_user.id)
    _save_setting('payment_channel', payment_channel, current_user.id)

    current_app.config['COINS_PER_1000_TOKENS'] = str(coins_per_1000)
    current_app.config['COINS_PER_YUAN'] = str(coins_per_yuan)
    current_app.config['REVIEW_AUDIT_COINS'] = str(review_audit)
    current_app.config['MIN_RECHARGE_AMOUNT_YUAN'] = str(min_recharge)

    db.session.commit()
    flash('费率与付费设置已更新。', 'success')
    return redirect(url_for('admin.admin_dashboard', tab='pricing'))


@admin_bp.route('/settings/campaign', methods=['POST'])
@login_required
@admin_required
def admin_update_campaign():
    if not _has_permission('can_manage_pricing'):
        flash('当前账号没有充值活动配置权限。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='pricing'))

    raw = (request.form.get('campaign') or '').strip()
    if not raw:
        flash('充值活动配置不能为空。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='pricing'))

    try:
        parsed = json.loads(raw)
    except Exception:
        flash('充值活动配置必须是合法 JSON。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='pricing'))

    _save_setting('recharge_campaign_config', json.dumps(parsed, ensure_ascii=False, indent=2), current_user.id)
    db.session.commit()
    flash('充值活动配置已保存。', 'success')
    return redirect(url_for('admin.admin_dashboard', tab='pricing'))


@admin_bp.route('/settings/user-log-policy', methods=['POST'])
@login_required
@admin_required
def admin_update_user_log_policy():
    if not _has_permission('can_view_logs'):
        flash('当前账号没有日志配置权限。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='logs'))

    mode = (request.form.get('user_action_log_mode') or DEFAULT_USER_ACTION_LOG_MODE).strip().lower()
    if mode not in USER_ACTION_LOG_MODES:
        flash('无效的用户日志采集策略。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='logs'))

    _save_setting('user_action_log_mode', mode, current_user.id)
    db.session.commit()
    flash(f'用户操作日志采集策略已更新为：{USER_LOG_MODE_LABELS.get(mode, mode)}。', 'success')
    return redirect(url_for('admin.admin_dashboard', tab='logs'))


@admin_bp.route('/user/<int:user_id>/coins', methods=['POST'])
@login_required
@admin_required
def admin_adjust_user_coins(user_id):
    if not _has_permission('can_manage_wallet_ops'):
        flash('当前账号没有代币调整权限。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='users'))

    user = User.query.get(user_id)
    if not user:
        flash('用户不存在。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='users'))

    op_type = (request.form.get('op_type') or '').strip().lower()
    remark = (request.form.get('remark') or '').strip()
    try:
        coins = int(request.form.get('coins', '0'))
    except ValueError:
        flash('代币数量必须是整数。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='users'))

    try:
        wallet, _ = admin_adjust_wallet(
            user.id,
            op_type=op_type,
            coins=coins,
            remark=remark,
            operator_id=current_user.id,
            idempotency_key=f'admin-op:{current_user.id}:{user.id}:{op_type}:{coins}:{datetime.utcnow().timestamp()}'
        )
        db.session.commit()
        flash(f'代币操作成功：{user.username} {op_type} {coins}，当前可用 {wallet.available_coins}。', 'success')
    except InsufficientBalanceError as error:
        db.session.rollback()
        flash(str(error), 'danger')
    except Exception as error:
        db.session.rollback()
        flash(f'代币操作失败：{error}', 'danger')

    return redirect(url_for('admin.admin_dashboard', tab='users'))


@admin_bp.route('/user/<int:user_id>/permission', methods=['POST'])
@login_required
@admin_required
def admin_update_user_permission(user_id):
    if not _has_permission('can_manage_users'):
        flash('当前账号没有权限管理能力。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='permissions'))

    user = User.query.get(user_id)
    if not user:
        flash('用户不存在。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='permissions'))

    if not user.is_admin:
        flash('该用户不是管理员，无需配置系统权限。', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='permissions'))

    row = _get_permission_row(user.id)
    changed = []
    for key in PERMISSION_LABELS.keys():
        value = request.form.get(key) == 'on'
        setattr(row, key, value)
        changed.append(f'{key}={value}')
    row.updated_by = current_user.id

    db.session.commit()
    flash(f'已更新管理员 {user.username} 的系统权限。', 'success')
    return redirect(url_for('admin.admin_dashboard', tab='permissions'))
