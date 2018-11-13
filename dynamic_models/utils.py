"""
Various utility functions for the dynamic models app.
"""
from functools import lru_cache
from django.conf import settings
from django.apps import apps
from django.core.cache import cache
from django.utils import timezone
from django.utils.text import slugify

from . import signals
from .exceptions import InvalidConfigurationError


def default_fields():
    """
    Returns the DEFAULT_FIELDS setting.
    """
    return settings.DYNAMIC_MODELS.get('DEFAULT_FIELDS', {})

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
    Deletes a model from Django's app registry. Returns the deleted model if
    found or None if it was not registered.
    """
    return apps.all_models[app_label].pop(model_name, None)

def has_current_schema(schema, model):
    """
    Checks that the last time the schema we changed is earlier than model
    definition.
    """
    return schema.modified < model._declared
