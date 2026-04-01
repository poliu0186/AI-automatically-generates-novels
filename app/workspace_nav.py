import json

from app.models import AdminSetting

WORKSPACE_NAV_SETTING_KEY = 'workspace_nav_enabled_pages'

WORKSPACE_NAV_ITEMS = [
    {'key': 'basic', 'label': '作品设定', 'icon': '🧱', 'group': 'top'},
    {'key': 'prompts', 'label': '创作策略', 'icon': '🧠', 'group': 'top'},
    {'key': 'outline', 'label': '生成大纲', 'icon': '🗺️', 'group': 'top'},
    {'key': 'chapters', 'label': '写作章节', 'icon': '📚', 'group': 'top'},
    {'key': 'export', 'label': '导出成稿', 'icon': '📦', 'group': 'top'},
    {'key': 'review', 'label': '自动审核', 'icon': '✅', 'group': 'top'},
    {'key': 'advanced-contextmenu', 'label': '右键设置', 'icon': '🧩', 'group': 'advanced'},
    {'key': 'advanced-autosplit', 'label': '自动拆书', 'icon': '✂️', 'group': 'advanced'},
    {'key': 'advanced-knowledge', 'label': '知识库', 'icon': '📖', 'group': 'advanced'},
    {'key': 'advanced-mindmap', 'label': '思维导图大纲', 'icon': '🧭', 'group': 'advanced'},
    {'key': 'wallet', 'label': '用户中心', 'icon': '💰', 'group': 'top'},
]

WORKSPACE_NAV_ORDER = [item['key'] for item in WORKSPACE_NAV_ITEMS]
WORKSPACE_NAV_ITEM_MAP = {item['key']: item for item in WORKSPACE_NAV_ITEMS}


def _default_enabled_pages():
    return list(WORKSPACE_NAV_ORDER)


def _normalize_enabled_pages(raw_value):
    if not raw_value:
        return _default_enabled_pages()

    parsed = None
    try:
        parsed = json.loads(raw_value)
    except Exception:
        parsed = None

    pages = []
    if isinstance(parsed, dict):
        values = parsed.get('enabled_pages')
        if isinstance(values, list):
            pages = values
    elif isinstance(parsed, list):
        pages = parsed

    normalized = []
    for value in pages:
        key = str(value or '').strip()
        if key in WORKSPACE_NAV_ITEM_MAP and key not in normalized:
            normalized.append(key)

    if not normalized:
        return _default_enabled_pages()

    return [key for key in WORKSPACE_NAV_ORDER if key in normalized]


def get_workspace_enabled_pages():
    row = AdminSetting.query.filter_by(key=WORKSPACE_NAV_SETTING_KEY).first()
    raw = row.value if row and row.value is not None else ''
    return _normalize_enabled_pages(raw)


def build_workspace_nav_view_data():
    enabled_pages = get_workspace_enabled_pages()
    enabled_set = set(enabled_pages)

    top_items = [item for item in WORKSPACE_NAV_ITEMS if item['group'] == 'top' and item['key'] in enabled_set]
    advanced_items = [item for item in WORKSPACE_NAV_ITEMS if item['group'] == 'advanced' and item['key'] in enabled_set]

    default_page = enabled_pages[0] if enabled_pages else 'basic'
    user_center_page = 'wallet' if 'wallet' in enabled_set else default_page

    return {
        'enabled_pages': enabled_pages,
        'top_items': top_items,
        'advanced_items': advanced_items,
        'default_page': default_page,
        'user_center_page': user_center_page,
    }


def serialize_enabled_pages(enabled_pages):
    clean = []
    for value in enabled_pages or []:
        key = str(value or '').strip()
        if key in WORKSPACE_NAV_ITEM_MAP and key not in clean:
            clean.append(key)

    ordered = [key for key in WORKSPACE_NAV_ORDER if key in clean]
    return json.dumps({'enabled_pages': ordered}, ensure_ascii=False)
