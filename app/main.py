from flask import Blueprint, render_template, redirect, url_for, abort
from flask_login import login_required, current_user

from app.workspace_nav import build_workspace_nav_view_data

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def home():
    if getattr(current_user, 'is_admin', False):
        return redirect(url_for('admin.admin_dashboard'))
    nav_data = build_workspace_nav_view_data()
    return render_template(
        'workspace_shell.html',
        user=current_user,
        active_page=nav_data['default_page'],
        nav_top_items=nav_data['top_items'],
        nav_advanced_items=nav_data['advanced_items'],
        enabled_pages=nav_data['enabled_pages'],
        user_center_page=nav_data['user_center_page'],
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


@main_bp.route('/test')
def test():
    return render_template('test_download.html')
