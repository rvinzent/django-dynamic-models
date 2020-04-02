from django.conf import settings


def default_fields():
    return _settings().get('DEFAULT_FIELDS', {})


def default_charfield_max_length():
    return _settings().get('DEFAULT_CHARFIELD_MAX_LENGTH', 255)


def cache_key_prefix():
    return _settings().get('CACHE_KEY_PREFIX', 'dyanmic_models_')


def cache_timeout():
    return _settings().get('CACHE_TIMEOUT', 60 * 60 * 24)


def _settings():
    return getattr(settings, 'DYNAMIC_MODELS', {})
