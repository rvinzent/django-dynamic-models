"""Various utility functions for the dynamic_models app.

`default_fields`     -- return DEFAULT_FIELDS setting
`get_cached_model`   -- return model from app registry
`unregister model`   -- remove model from app registry
`has_current_schema` -- check if model's schema is updated
"""
from django.conf import settings
from django.apps import apps
from . import exceptions

DEFAULT_MAX_LENGTH = 255

def default_fields():
    """Returns the DEFAULT_FIELDS setting."""
    return _settings().get('DEFAULT_FIELDS', {})

def default_max_length():
    """Returns the default max_length value from the settings or 255."""
    return _settings().get('DEFAULT_MAX_LENGTH', DEFAULT_MAX_LENGTH)

def _settings():
    return getattr(settings, 'DYNAMIC_MODELS', {})

def get_model(app_label, model_name):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError as err:
        raise exceptions.ModelDoesNotExistError() from err
