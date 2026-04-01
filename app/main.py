from flask import Blueprint, render_template, redirect, url_for, abort
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def home():
    if getattr(current_user, 'is_admin', False):
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('workspace_shell.html', user=current_user, active_page='basic')


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

    return render_template('workspace_page.html', user=current_user, active_page=page)


@main_bp.route('/workspace/<page>')
@login_required
def workspace_page_legacy(page):
    return redirect(url_for('main.workspace_page', page=page))


@main_bp.route('/test')
def test():
    return render_template('test_download.html')
