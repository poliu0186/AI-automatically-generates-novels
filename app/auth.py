from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, login_manager
from app.models import User

auth_bp = Blueprint('auth', __name__)


def get_user_by_username(username):
    return User.query.filter_by(username=username).first()


def create_user(username, password, is_admin=False):
    password_hash = generate_password_hash(password)
    user = User(username=username, password_hash=password_hash, is_admin=is_admin)
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


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = get_user_by_username(username)

        if user and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('该账号已被禁用，如有疑问请联系管理员。', 'danger')
            else:
                login_user(user)
                flash('登录成功。', 'success')
                return redirect(request.args.get('next') or url_for('main.home'))
        else:
            flash('用户名或密码错误，请重试。', 'danger')

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not username or not password:
            flash('用户名和密码不能为空。', 'danger')
        elif password != confirm_password:
            flash('两次输入的密码不一致。', 'danger')
        elif get_user_by_username(username):
            flash('该用户名已存在，请更换。', 'danger')
        else:
            user_id = create_user(username, password)
            if user_id:
                flash('注册成功，请登录。', 'success')
                return redirect(url_for('auth.login'))
            flash('注册失败，请稍后重试。', 'danger')

    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已退出登录。', 'success')
    return redirect(url_for('auth.login'))
