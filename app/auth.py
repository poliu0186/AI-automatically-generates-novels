import hashlib
import random
import secrets
import smtplib
import time
from datetime import datetime, timedelta
from email.message import EmailMessage

from flask import Blueprint, Response, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import login_user, login_required, logout_user, current_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash

from app.activity_logging import log_user_action
from app.extensions import db, login_manager
from app.models import PasswordResetRequest, User

auth_bp = Blueprint('auth', __name__)

ADMIN_LOGIN_OTP_SESSION_KEY = 'admin_login_otp_payload'


def _is_safe_redirect_url(target):
    """Reject absolute URLs and open redirects; allow only relative paths on the same host."""
    if not target:
        return False
    from urllib.parse import urlparse
    parsed = urlparse(target)
    # Only allow relative paths (no scheme, no netloc)
    if parsed.scheme or parsed.netloc:
        return False
    return True


def _post_login_redirect(user, next_url=None):
    if next_url and _is_safe_redirect_url(next_url):
        return redirect(next_url)
    if getattr(user, 'is_admin', False):
        return redirect(url_for('admin.admin_dashboard'))
    return redirect(url_for('main.home'))


def _otp_hash(code):
    return hashlib.sha256(str(code or '').encode('utf-8')).hexdigest()


def _admin_otp_length():
    return max(4, min(int(current_app.config.get('ADMIN_OTP_LENGTH', 6) or 6), 8))


def _admin_otp_payload():
    payload = session.get(ADMIN_LOGIN_OTP_SESSION_KEY)
    if not isinstance(payload, dict):
        return None
    return payload


def _clear_admin_otp_payload():
    session.pop(ADMIN_LOGIN_OTP_SESSION_KEY, None)


def _clear_login_captcha_payload():
    session.pop('login_captcha_code', None)
    session.pop('login_captcha_at', None)


def _clear_auth_transient_state():
    _clear_admin_otp_payload()
    _clear_login_captcha_payload()
    session.pop('forgot_password_cooldowns', None)


def _generate_admin_otp_code():
    digits = '0123456789'
    return ''.join(secrets.choice(digits) for _ in range(_admin_otp_length()))


def _send_admin_login_otp_email(to_email, code):
    host = (current_app.config.get('MAIL_HOST') or '').strip()
    port = int(current_app.config.get('MAIL_PORT', 465))
    username = (current_app.config.get('MAIL_USERNAME') or '').strip()
    password = current_app.config.get('MAIL_PASSWORD') or ''
    sender = (current_app.config.get('MAIL_SENDER') or username).strip()
    use_tls = bool(current_app.config.get('MAIL_USE_TLS', False))
    timeout_seconds = int(current_app.config.get('MAIL_TIMEOUT_SECONDS', 8))

    if not host or not sender or not username or not password:
        current_app.logger.warning('MAIL_* config missing; skip sending admin OTP email')
        return False

    ttl = int(current_app.config.get('ADMIN_OTP_TTL_SECONDS', 300) or 300)
    msg = EmailMessage()
    msg['Subject'] = '小说创作助手 - 管理员登录验证码'
    msg['From'] = sender
    msg['To'] = to_email
    msg.set_content(
        '管理员您好，\n\n'
        '您正在登录后台管理系统，请输入以下验证码完成二次验证：\n\n'
        f'{code}\n\n'
        f'验证码 {ttl} 秒内有效。若非本人操作，请立即修改密码。\n'
    )

    try:
        if use_tls:
            with smtplib.SMTP(host, port, timeout=timeout_seconds) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(host, port, timeout=timeout_seconds) as server:
                server.login(username, password)
                server.send_message(msg)
        return True
    except Exception:
        current_app.logger.exception('Failed to send admin OTP email')
        return False


def _issue_admin_login_otp(user, next_url=''):
    email = normalize_email(getattr(user, 'email', None))
    if not email:
        return False, '管理员账号未配置邮箱，无法进行二次验证。'

    now_ts = int(time.time())
    cooldown = max(int(current_app.config.get('ADMIN_OTP_RESEND_COOLDOWN_SECONDS', 60) or 60), 10)
    existing = _admin_otp_payload()
    if existing and int(existing.get('user_id') or 0) == int(user.id):
        sent_at = int(existing.get('sent_at') or 0)
        if now_ts - sent_at < cooldown:
            remain = cooldown - (now_ts - sent_at)
            return False, f'验证码已发送，请 {remain} 秒后再试。'

    code = _generate_admin_otp_code()
    if not _send_admin_login_otp_email(email, code):
        return False, '验证码发送失败，请检查邮箱配置后重试。'

    ttl = max(int(current_app.config.get('ADMIN_OTP_TTL_SECONDS', 300) or 300), 60)
    session[ADMIN_LOGIN_OTP_SESSION_KEY] = {
        'user_id': int(user.id),
        'code_hash': _otp_hash(code),
        'expires_at': now_ts + ttl,
        'sent_at': now_ts,
        'next': next_url or '',
    }
    return True, '验证码已发送到管理员邮箱，请输入验证码继续。'


def _admin_otp_view_model():
    payload = _admin_otp_payload() or {}
    user_id = int(payload.get('user_id') or 0)
    pending_user = User.query.get(user_id) if user_id else None
    return {
        'otp_required': bool(payload),
        'pending_username': pending_user.username if pending_user else '',
        'pending_next': str(payload.get('next') or ''),
    }


def _complete_login(user, *, action_name='login_success', detail='账号登录成功'):
    clear_user_login_failures(user)
    user.login_count = int(user.login_count or 0) + 1
    log_user_action(user.id, action_name, detail)
    login_user(user)
    db.session.commit()


def get_user_by_username(username):
    return User.query.filter_by(username=username).first()


def normalize_email(email):
    value = (email or '').strip().lower()
    return value or None


def get_user_by_email(email):
    normalized = normalize_email(email)
    if not normalized:
        return None
    return User.query.filter_by(email=normalized).first()


def create_user(username, password, email=None, is_admin=False):
    password_hash = generate_password_hash(password)
    user = User(
        username=username,
        email=normalize_email(email),
        password_hash=password_hash,
        is_admin=is_admin
    )
    try:
        db.session.add(user)
        db.session.commit()
        return user.id
    except Exception:
        db.session.rollback()
        return None


def admin_required(view):
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            flash('需要管理员权限才能访问此页面。', 'danger')
            return redirect(url_for('main.home'))
        return view(*args, **kwargs)
    wrapped_view.__name__ = view.__name__
    return wrapped_view


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def get_password_strength_error(password):
    if len(password or '') < 10:
        return '密码长度至少 10 位。'
    if not any(ch.islower() for ch in password):
        return '密码至少包含 1 个小写字母。'
    if not any(ch.isupper() for ch in password):
        return '密码至少包含 1 个大写字母。'
    if not any(ch.isdigit() for ch in password):
        return '密码至少包含 1 个数字。'
    if not any((not ch.isalnum()) for ch in password):
        return '密码至少包含 1 个特殊字符。'
    return None


def check_and_auto_unlock_user(user):
    if not user or not user.locked_until:
        return False
    if user.locked_until > datetime.utcnow():
        return False
    user.locked_until = None
    user.failed_login_attempts = 0
    db.session.commit()
    return True


def lock_remaining_seconds(user):
    if not user or not user.locked_until:
        return 0
    delta = int((user.locked_until - datetime.utcnow()).total_seconds())
    return max(delta, 0)


def register_user_login_failure(user):
    if not user:
        return False
    check_and_auto_unlock_user(user)
    user.failed_login_attempts = int(user.failed_login_attempts or 0) + 1
    max_attempts = max(int(current_app.config.get('LOGIN_MAX_ATTEMPTS', 10) or 10), 1)
    is_locked_now = False
    if user.failed_login_attempts >= max_attempts:
        user.locked_until = datetime.utcnow() + timedelta(hours=24)
        is_locked_now = True
    db.session.commit()
    return is_locked_now


def clear_user_login_failures(user):
    if not user:
        return
    if user.failed_login_attempts or user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
        db.session.commit()


def generate_captcha_code(length=5):
    alphabet = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
    return ''.join(secrets.choice(alphabet) for _ in range(max(4, length)))


def build_captcha_svg(code):
    width = 140
    height = 44
    noise_lines = []
    for _ in range(6):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        color = random.choice(['#c5d3ef', '#d8c7f4', '#c7ead5', '#f4d9c7'])
        noise_lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1"/>')

    chars = []
    step = width // (len(code) + 1)
    for idx, char in enumerate(code):
        x = (idx + 1) * step + random.randint(-4, 4)
        y = random.randint(28, 34)
        rotate = random.randint(-20, 20)
        fill = random.choice(['#2d4b8f', '#1f7a5a', '#8a3b2f', '#5f3d99'])
        chars.append(
            f'<text x="{x}" y="{y}" fill="{fill}" font-size="26" '
            f'font-family="Verdana" transform="rotate({rotate} {x} {y})">{char}</text>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" rx="8" ry="8" fill="#f5f8ff"/>'
        + ''.join(noise_lines)
        + ''.join(chars)
        + '</svg>'
    )


def is_login_captcha_valid(captcha_input):
    expected = (session.get('login_captcha_code') or '').strip().upper()
    generated_at = float(session.get('login_captcha_at') or 0)
    user_input = (captcha_input or '').strip().upper()
    ttl = int(current_app.config.get('LOGIN_CAPTCHA_TTL_SECONDS', 180))

    _clear_login_captcha_payload()

    if not expected or not generated_at:
        return False
    if time.time() - generated_at > ttl:
        return False
    return expected == user_input


def get_reset_token_serializer():
    return URLSafeTimedSerializer(current_app.secret_key, salt='password-reset-salt')


def build_reset_link(user):
    serializer = get_reset_token_serializer()
    nonce = secrets.token_urlsafe(16)
    token = serializer.dumps({'uid': user.id, 'nonce': nonce})
    ttl = int(current_app.config.get('RESET_PASSWORD_EXPIRE_SECONDS', 1800))
    req = PasswordResetRequest(
        user_id=user.id,
        token_hash=hashlib.sha256(token.encode('utf-8')).hexdigest(),
        expires_at=datetime.utcnow() + timedelta(seconds=ttl)
    )
    db.session.add(req)
    db.session.commit()
    return token, url_for('auth.reset_password', token=token, _external=True)


def send_password_reset_email(to_email, reset_link):
    host = (current_app.config.get('MAIL_HOST') or '').strip()
    port = int(current_app.config.get('MAIL_PORT', 465))
    username = (current_app.config.get('MAIL_USERNAME') or '').strip()
    password = current_app.config.get('MAIL_PASSWORD') or ''
    sender = (current_app.config.get('MAIL_SENDER') or username).strip()
    use_tls = bool(current_app.config.get('MAIL_USE_TLS', False))
    timeout_seconds = int(current_app.config.get('MAIL_TIMEOUT_SECONDS', 8))

    if not host or not sender or not username or not password:
        current_app.logger.warning('MAIL_* config missing (host/sender/username/password); skip sending reset email')
        return False

    msg = EmailMessage()
    msg['Subject'] = '小说创作助手 - 密码重置'
    msg['From'] = sender
    msg['To'] = to_email
    msg.set_content(
        '您好，\n\n'
        '我们收到了重置密码请求。请在有效期内打开下方链接设置新密码：\n\n'
        f'{reset_link}\n\n'
        '如果这不是您的操作，请忽略本邮件。\n'
    )

    try:
        if use_tls:
            with smtplib.SMTP(host, port, timeout=timeout_seconds) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                if username:
                    server.login(username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(host, port, timeout=timeout_seconds) as server:
                if username:
                    server.login(username, password)
                server.send_message(msg)
        return True
    except Exception:
        current_app.logger.exception('Failed to send password reset email')
        return False


def verify_reset_token(token):
    serializer = get_reset_token_serializer()
    ttl = int(current_app.config.get('RESET_PASSWORD_EXPIRE_SECONDS', 1800))
    try:
        payload = serializer.loads(token, max_age=ttl)
    except SignatureExpired:
        return None, '链接已过期'
    except BadSignature:
        return None, '链接无效'

    user_id = payload.get('uid')
    if not user_id:
        return None, '链接无效'

    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    req = PasswordResetRequest.query.filter_by(token_hash=token_hash).first()
    if not req:
        return None, '链接无效'
    if req.used_at is not None:
        return None, '该链接已被使用'
    if req.expires_at <= datetime.utcnow():
        return None, '链接已过期'
    if req.user_id != int(user_id):
        return None, '链接无效'

    user = User.query.get(req.user_id)
    if not user:
        return None, '用户不存在'
    return {'user': user, 'request': req}, None


def _get_forgot_password_cooldowns():
    raw = session.get('forgot_password_cooldowns')
    if not isinstance(raw, dict):
        raw = {}
    return raw


def get_forgot_password_cooldown_remaining(username):
    normalized = (username or '').strip().lower()
    if not normalized:
        return 0
    cooldowns = _get_forgot_password_cooldowns()
    until = float(cooldowns.get(normalized, 0) or 0)
    return max(0, int(until - time.time()))


def mark_forgot_password_cooldown(username):
    normalized = (username or '').strip().lower()
    if not normalized:
        return
    cooldown_seconds = int(current_app.config.get('RESET_PASSWORD_RESEND_COOLDOWN_SECONDS', 60))
    cooldowns = _get_forgot_password_cooldowns()
    cooldowns[normalized] = time.time() + max(1, cooldown_seconds)
    session['forgot_password_cooldowns'] = cooldowns


@auth_bp.route('/captcha.svg')
def login_captcha():
    code = generate_captcha_code()
    session['login_captcha_code'] = code
    session['login_captcha_at'] = time.time()
    svg = build_captcha_svg(code)
    return Response(
        svg,
        mimetype='image/svg+xml',
        headers={
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
            'Pragma': 'no-cache'
        }
    )


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return _post_login_redirect(current_user)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        captcha = request.form.get('captcha', '').strip()
        user = get_user_by_username(username)

        if user:
            check_and_auto_unlock_user(user)
            remain = lock_remaining_seconds(user)
            if remain > 0:
                hours = max(1, int((remain + 3599) / 3600))
                flash(f'该账号已被锁定，请 {hours} 小时后重试，或联系管理员解锁。', 'danger')
                return render_template('login.html')

        if not is_login_captcha_valid(captcha):
            flash('图形验证码错误或已过期，请重试。', 'danger')
            return render_template('login.html')

        if user and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('该账号已被禁用，如有疑问请联系管理员。', 'danger')
            elif user.is_admin:
                flash('管理员账号请使用后台专用登录入口。', 'danger')
            else:
                _complete_login(user)
                return _post_login_redirect(user, request.args.get('next'))
        else:
            locked_now = register_user_login_failure(user)
            if locked_now:
                max_attempts = max(int(current_app.config.get('LOGIN_MAX_ATTEMPTS', 10) or 10), 1)
                flash(f'连续 {max_attempts} 次登录失败，账号已锁定 24 小时。可联系管理员解锁。', 'danger')
            else:
                flash('用户名或密码错误，请重试。', 'danger')

    return render_template('login.html')


@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return _post_login_redirect(current_user)

    if request.method == 'POST':
        step = (request.form.get('step') or 'password').strip().lower()

        if step == 'otp':
            payload = _admin_otp_payload()
            code = (request.form.get('otp_code') or '').strip()
            if not payload:
                flash('验证码会话已失效，请重新登录。', 'danger')
                return render_template('admin_login.html', **_admin_otp_view_model())

            now_ts = int(time.time())
            if now_ts > int(payload.get('expires_at') or 0):
                _clear_admin_otp_payload()
                flash('验证码已过期，请重新登录。', 'danger')
                return render_template('admin_login.html', **_admin_otp_view_model())

            if _otp_hash(code) != str(payload.get('code_hash') or ''):
                flash('验证码不正确，请重试。', 'danger')
                return render_template('admin_login.html', **_admin_otp_view_model())

            user = User.query.get(int(payload.get('user_id') or 0))
            if not user or not user.is_active or not user.is_admin:
                _clear_admin_otp_payload()
                flash('管理员账号状态异常，请联系系统管理员。', 'danger')
                return render_template('admin_login.html', **_admin_otp_view_model())

            next_url = str(payload.get('next') or request.form.get('next') or '')
            _clear_admin_otp_payload()
            _complete_login(user, action_name='admin_login_success', detail='管理员后台登录成功')
            flash('管理员登录成功。', 'success')
            return _post_login_redirect(user, next_url)

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        captcha = request.form.get('captcha', '').strip()
        user = get_user_by_username(username)

        if user:
            check_and_auto_unlock_user(user)
            remain = lock_remaining_seconds(user)
            if remain > 0:
                hours = max(1, int((remain + 3599) / 3600))
                flash(f'该账号已被锁定，请 {hours} 小时后重试，或联系管理员解锁。', 'danger')
                return render_template('admin_login.html')

        if not is_login_captcha_valid(captcha):
            flash('图形验证码错误或已过期，请重试。', 'danger')
            return render_template('admin_login.html')

        if user and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('该账号已被禁用，如有疑问请联系更高权限管理员。', 'danger')
            elif not user.is_admin:
                flash('当前账号不是管理员，请使用普通用户登录入口。', 'danger')
            else:
                if current_app.config.get('ADMIN_2FA_ENABLED', True):
                    ok, message = _issue_admin_login_otp(user, next_url=request.args.get('next', ''))
                    flash(message, 'success' if ok else 'danger')
                    return render_template('admin_login.html', **_admin_otp_view_model())
                _complete_login(user, action_name='admin_login_success', detail='管理员后台登录成功')
                return _post_login_redirect(user, request.args.get('next'))
        else:
            locked_now = register_user_login_failure(user)
            if locked_now:
                max_attempts = max(int(current_app.config.get('LOGIN_MAX_ATTEMPTS', 10) or 10), 1)
                flash(f'连续 {max_attempts} 次登录失败，账号已锁定 24 小时。可联系管理员解锁。', 'danger')
            else:
                flash('用户名或密码错误，请重试。', 'danger')

    return render_template('admin_login.html', **_admin_otp_view_model())


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = normalize_email(request.form.get('email', ''))
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not username or not password or not email:
            flash('用户名、邮箱和密码不能为空。', 'danger')
        elif password != confirm_password:
            flash('两次输入的密码不一致。', 'danger')
        elif get_password_strength_error(password):
            flash(get_password_strength_error(password), 'danger')
        elif get_user_by_username(username):
            flash('该用户名已存在，请更换。', 'danger')
        elif get_user_by_email(email):
            flash('该邮箱已被注册，请使用其他邮箱。', 'danger')
        else:
            user_id = create_user(username, password, email=email)
            if user_id:
                flash('注册成功，请登录。', 'success')
                return redirect(url_for('auth.login'))
            flash('注册失败，请稍后重试。', 'danger')

    return render_template('register.html')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    username = request.values.get('username', '').strip()
    cooldown_seconds = get_forgot_password_cooldown_remaining(username)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = normalize_email(request.form.get('email', ''))
        cooldown_seconds = get_forgot_password_cooldown_remaining(username)

        if not username:
            flash('请先输入登录用户名，再进行找回密码。', 'danger')
            return render_template('forgot_password.html', username=username, cooldown_seconds=cooldown_seconds)

        if cooldown_seconds > 0:
            flash(f'邮件刚发送过，请 {cooldown_seconds} 秒后再试。', 'danger')
            return render_template('forgot_password.html', username=username, cooldown_seconds=cooldown_seconds)

        if not email:
            flash('请输入注册邮箱。', 'danger')
            return render_template('forgot_password.html', username=username, cooldown_seconds=cooldown_seconds)

        user = get_user_by_username(username)
        sent = False
        if user and user.is_active and normalize_email(user.email) == email:
            try:
                _, reset_link = build_reset_link(user)
                sent = send_password_reset_email(email, reset_link)
            except Exception:
                db.session.rollback()
                current_app.logger.exception('Create password reset request failed')

        if sent:
            mark_forgot_password_cooldown(username)
            cooldown_seconds = get_forgot_password_cooldown_remaining(username)
            flash('重置链接已发送到邮箱，请注意查收。', 'success')
        else:
            flash('邮件发送失败或邮箱信息不匹配，请检查后重试。', 'danger')
            if not (current_app.config.get('MAIL_HOST') and current_app.config.get('MAIL_SENDER') and current_app.config.get('MAIL_USERNAME') and current_app.config.get('MAIL_PASSWORD')):
                flash('当前未配置邮件服务，暂时无法发送重置邮件，请联系管理员。', 'danger')

    return render_template('forgot_password.html', username=username, cooldown_seconds=cooldown_seconds)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    verified, err = verify_reset_token(token)
    if not verified:
        flash(err or '重置链接无效。', 'danger')
        return redirect(url_for('auth.forgot_password'))

    user = verified['user']
    reset_request = verified['request']

    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not password:
            flash('请输入新密码。', 'danger')
        elif get_password_strength_error(password):
            flash(get_password_strength_error(password), 'danger')
        elif password != confirm_password:
            flash('两次输入的密码不一致。', 'danger')
        else:
            user.password_hash = generate_password_hash(password)
            user.failed_login_attempts = 0
            user.locked_until = None
            reset_request.used_at = datetime.utcnow()
            db.session.commit()
            flash('密码重置成功，请使用新密码登录。', 'success')
            return redirect(url_for('auth.login'))

    return render_template('reset_password.html')


@auth_bp.route('/change-password', methods=['GET', 'POST'])
def change_password_page():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        captcha = request.form.get('captcha', '').strip()

        if not username:
            flash('请输入用户名。', 'danger')
            return render_template('change_password.html')
        if not current_password:
            flash('请输入当前密码。', 'danger')
            return render_template('change_password.html')
        if not new_password:
            flash('请输入新密码。', 'danger')
            return render_template('change_password.html')
        if new_password != confirm_password:
            flash('两次输入的新密码不一致。', 'danger')
            return render_template('change_password.html')
        if not is_login_captcha_valid(captcha):
            flash('图形验证码错误或已过期，请重试。', 'danger')
            return render_template('change_password.html')

        user = get_user_by_username(username)
        if not user:
            flash('用户不存在。', 'danger')
            return render_template('change_password.html')
        if not user.is_active:
            flash('该账号已被禁用，如有疑问请联系管理员。', 'danger')
            return render_template('change_password.html')
        if not check_password_hash(user.password_hash, current_password):
            flash('当前密码不正确。', 'danger')
            return render_template('change_password.html')
        if current_password == new_password:
            flash('新密码不能与当前密码相同。', 'danger')
            return render_template('change_password.html')

        strength_error = get_password_strength_error(new_password)
        if strength_error:
            flash(strength_error, 'danger')
            return render_template('change_password.html')

        user.password_hash = generate_password_hash(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        db.session.commit()
        flash('密码修改成功，请使用新密码登录。', 'success')
        return redirect(url_for('auth.login'))

    return render_template('change_password.html')


@auth_bp.route('/logout')
@login_required
def logout():
    _clear_auth_transient_state()
    logout_user()
    flash('您已退出登录。', 'success')
    return redirect(url_for('main.home'))


@auth_bp.route('/auth/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json(silent=True) or request.form.to_dict()
    current_password = (data.get('current_password') or '').strip()
    new_password = (data.get('new_password') or '').strip()
    confirm_password = (data.get('confirm_password') or '').strip()

    if not current_password:
        return jsonify({'error': '请输入当前密码。'}), 400
    if not new_password:
        return jsonify({'error': '请输入新密码。'}), 400
    if new_password != confirm_password:
        return jsonify({'error': '两次输入的新密码不一致。'}), 400
    if not check_password_hash(current_user.password_hash, current_password):
        return jsonify({'error': '当前密码不正确。'}), 400
    if current_password == new_password:
        return jsonify({'error': '新密码不能与当前密码相同。'}), 400

    strength_error = get_password_strength_error(new_password)
    if strength_error:
        return jsonify({'error': strength_error}), 400

    current_user.password_hash = generate_password_hash(new_password)
    current_user.failed_login_attempts = 0
    current_user.locked_until = None
    db.session.commit()
    return jsonify({'ok': True, 'message': '密码修改成功，请妥善保管新密码。'})
