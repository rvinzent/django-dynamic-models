"""
Various utility functions for the dynamic models app.
"""
from django.conf import settings
from django.apps import apps
from django.core.cache import cache
from django.utils.text import slugify
from . import signals


KEY_PREFIX = settings.DYNAMIC_MODELS.get('CACHE_KEY_PREFIX', 'dynamic_models')


def slugify_underscore(text):
    """
    Returns the slugified text with hyphens replaced by underscores.
    """
    return slugify(text).replace('-', '_')

def default_fields():
    """
    Returns the DEFAULT_FIELDS setting.
    """
    return settings.DYNAMIC_MODELS.get('DEFAULT_FIELDS', {})

def cache_key(model):
    """
    Returns the cache key for dynamic model caching.
    """
    return '{}_{}'.format(KEY_PREFIX, model._meta.model_name)

def get_cached_model(app_label, model_name):
    """
    Returns a model from Django's app registry or None if not found.
    """
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        pass

def unregister_dynamic_model(app_label, model_name):
    """
    Deletes a model from Django's app registry. Returns the deleted model if
    found or None if it was not registered.
    """
    try:
        return apps.all_models[app_label].pop(model_name)
    except LookupError:
        pass

def is_latest_model(model):
    """
    Checks the model hash from the provided model matches the latest hash stored
    in the cache. 
    """
    return cache.get(cache_key(model)) == model._hash

def set_latest_model(model, timeout=60*60*24*3):
    """
    Sets a model's hash as the latest value. The cache timeout is three days by
    default.
    """
    cache.set(cache_key(model), model._hash, timeout)

def delete_model_hash(model):
    """
    Removes a model's hash from the cache. Effectively forces a dynamic model to
    be regenerated the next time it is used.
    """
    cache.delete(cache_key(model))
