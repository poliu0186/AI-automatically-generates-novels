from pathlib import Path

from flask import Blueprint, render_template, redirect, url_for, abort, current_app, send_from_directory, request, flash
from flask_login import login_required, current_user

from app.workspace_nav import build_workspace_nav_view_data
from app.extensions import db
from app.models import UserMessage

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    if not current_user.is_authenticated:
        return render_template('home_landing.html')

    if getattr(current_user, 'is_admin', False):
        return redirect(url_for('admin.admin_dashboard'))
    nav_data = build_workspace_nav_view_data()
    unread_message_count = UserMessage.query.filter_by(user_id=current_user.id, status='replied').count()
    return render_template(
        'workspace_shell.html',
        user=current_user,
        active_page=nav_data['default_page'],
        nav_top_items=nav_data['top_items'],
        nav_advanced_items=nav_data['advanced_items'],
        enabled_pages=nav_data['enabled_pages'],
        user_center_page=nav_data['user_center_page'],
        unread_message_count=unread_message_count,
    )


@main_bp.route('/workspace/page/<page>')
@login_required
def workspace_page(page):
    if page == 'autosplit':
        return redirect(url_for('main.workspace_page', page='advanced-autosplit'))
    if page == 'advanced-review':
        return redirect(url_for('main.workspace_page', page='review'))

    allowed_pages = {
        'basic',
        'wallet',
        'prompts',
        'outline',
        'review',
        'advanced-autosplit',
        'chapters',
        'export',
        'advanced-contextmenu',
        'advanced-knowledge',
        'advanced-mindmap',
    }
    if page not in allowed_pages:
        abort(404)

    enabled_pages = set(build_workspace_nav_view_data()['enabled_pages'])
    if page not in enabled_pages:
        return redirect(url_for('main.home'))

    return render_template('workspace_page.html', user=current_user, active_page=page)


@main_bp.route('/workspace/<page>')
@login_required
def workspace_page_legacy(page):
    return redirect(url_for('main.workspace_page', page=page))


@main_bp.route('/messages', methods=['GET', 'POST'])
@login_required
def user_messages():
    if getattr(current_user, 'is_admin', False):
        return redirect(url_for('admin.admin_dashboard', tab='messages'))

    if request.method == 'POST':
        subject = (request.form.get('subject') or '').strip()
        content = (request.form.get('content') or '').strip()

        if not subject:
            flash('请填写问题主题。', 'danger')
        elif not content:
            flash('请填写问题内容。', 'danger')
        else:
            db.session.add(
                UserMessage(
                    user_id=current_user.id,
                    subject=subject[:120],
                    content=content[:4000],
                    status='open',
                )
            )
            db.session.commit()
            flash('消息已发送给管理员，我们会尽快处理并回复。', 'success')
            return redirect(url_for('main.user_messages'))

    marked_count = UserMessage.query.filter_by(user_id=current_user.id, status='replied').update(
        {'status': 'read'},
        synchronize_session=False,
    )
    if marked_count:
        db.session.commit()

    messages = UserMessage.query.filter_by(user_id=current_user.id).order_by(UserMessage.created_at.desc()).limit(100).all()
    return render_template('messages.html', user=current_user, messages=messages)


@main_bp.route('/media/jpg/<path:filename>')
def media_jpg(filename):
    jpg_dir = Path(current_app.root_path).parent / 'jpg'
    return send_from_directory(str(jpg_dir), filename)


@main_bp.route('/test')
def test():
    return render_template('test_download.html')
