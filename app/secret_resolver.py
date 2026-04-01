import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken


def _read_secret_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def _extract_cipher_text(value):
    text = (value or '').strip()
    if text.startswith('ENC(') and text.endswith(')'):
        return text[4:-1].strip()
    if text.startswith('ENC:'):
        return text[4:].strip()
    return None


def _read_master_key():
    key = os.environ.get('APP_CONFIG_MASTER_KEY')
    if key:
        return key.strip()

    key_file = os.environ.get('APP_CONFIG_MASTER_KEY_FILE')
    if key_file:
        return _read_secret_file(key_file).strip()

    return ''


@lru_cache(maxsize=1)
def _get_fernet():
    key = _read_master_key()
    if not key:
        return None
    return Fernet(key.encode('utf-8'))


def resolve_env_value(name, default=''):
    value = os.environ.get(name)
    if value is None:
        file_path = os.environ.get(f'{name}_FILE')
        if file_path:
            value = _read_secret_file(file_path)

    if value is None:
        value = default

    cipher_text = _extract_cipher_text(str(value))
    if not cipher_text:
        return str(value)

    fernet = _get_fernet()
    if not fernet:
        raise RuntimeError(
            f'Encrypted config detected for {name}, but APP_CONFIG_MASTER_KEY/APP_CONFIG_MASTER_KEY_FILE is missing'
        )

    try:
        plaintext = fernet.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
    except InvalidToken as ex:
        raise RuntimeError(f'Failed to decrypt encrypted config for {name}') from ex
    return plaintext


def resolve_env_bool(name, default=False):
    value = resolve_env_value(name, '1' if default else '0')
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def resolve_env_int(name, default=0):
    value = resolve_env_value(name, str(default))
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)
