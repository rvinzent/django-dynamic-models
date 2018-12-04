"""Various utility functions for the dynamic_models app."""
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

def get_registered_model(model_schema):
    """Get a model from Django's app registry."""
    try:
        return apps.get_model(model_schema.app_label, model_schema.model_name)
    except LookupError as err:
        raise exceptions.ModelDoesNotExistError() from err
