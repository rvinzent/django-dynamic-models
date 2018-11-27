"""
Various utility functions for the dynamic models app.
"""
from django.conf import settings
from django.apps import apps

from . import signals
from .exceptions import InvalidConfigurationError


def default_fields():
    """
    Returns the DEFAULT_FIELDS setting.
    """
    try:
        return settings.DYNAMIC_MODELS.get('DEFAULT_FIELDS', {})
    except AttributeError:
        return {}

def get_cached_model(app_label, model_name):
    """
    Returns a model from Django's app registry or None if not found.
    """
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        pass

def unregister_model(app_label, model_name):
    """
    Deletes a model from Django's app registry and disconnects any model
    signals. Returns False if the model does not exist and True if it was
    unregistered successfully.
    """
    try:
        old_model = apps.get_model(app_label, model_name)
        del apps.all_models[app_label][model_name]
    except (KeyError, LookupError):
        return False
    signals.disconnect_dynamic_model(old_model)
    return True


def has_current_schema(schema, model):
    """
    Checks that the last time the schema we changed is earlier than model
    definition.
    """
    return schema.modified < model._declared
