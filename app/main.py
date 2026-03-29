from flask import Blueprint, render_template, redirect, url_for, abort
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def home():
    return render_template('workspace_shell.html', user=current_user, active_page='basic')


@main_bp.route('/workspace/page/<page>')
@login_required
def workspace_page(page):
    allowed_pages = {
        'basic',
        'prompts',
        'outline',
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
