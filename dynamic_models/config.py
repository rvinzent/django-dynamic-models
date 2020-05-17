from django.conf import settings


def default_fields():
    return _settings().get('DEFAULT_FIELDS', {})


def default_max_length():
    return _settings().get('DEFAULT_CHAR_FIELD_MAX_LENGTH', 255)


def cache_key_prefix():
    return _settings().get('CACHE_KEY_PREFIX', 'dynamic_models_schema_')


def cache_timeout():
    default_timeout = 60 * 60 * 24  # 24 hours
    return _settings().get('CACHE_TIMEOUT', default_timeout)


def _settings():
    return getattr(settings, 'DYNAMIC_MODELS', {})
