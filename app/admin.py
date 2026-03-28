from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.auth import admin_required
from app.extensions import db
from app.models import User

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@login_required
@admin_required
def admin_dashboard():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin.html', users=users)


@admin_bp.route('/user/<int:user_id>/action', methods=['POST'])
@login_required
@admin_required
def admin_user_action(user_id):
    action = request.form.get('action')
    user = User.query.get(user_id)
    if not user:
        flash('用户不存在。', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    if user.id == current_user.id and action in ('toggle_active', 'delete', 'toggle_admin'):
        flash('管理员不能修改自身状态。', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    if action == 'toggle_admin':
        user.is_admin = not user.is_admin
        flash(f'已将用户 {user.username} 的管理员权限设置为 {user.is_admin}。', 'success')
    elif action == 'toggle_active':
        user.is_active = not user.is_active
        flash(f'已将用户 {user.username} 的状态设置为 {"启用" if user.is_active else "禁用"}。', 'success')
    elif action == 'delete':
        db.session.delete(user)
        flash(f'已删除用户 {user.username}。', 'success')
    else:
        flash('未知操作。', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    db.session.commit()
    return redirect(url_for('admin.admin_dashboard'))
