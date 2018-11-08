"""
Various utility functions for the dynamic models app.
"""
from django.conf import settings
from django.apps import apps
from django.core.cache import cache
from django.utils.text import slugify
from .exceptions import OutdatedModelError


KEY_PREFIX = settings.DYNAMIC_MODELS.get('CACHE_KEY_PREFIX', 'dynamic_models')


def slugify_underscore(text):
    """
    Returns the slugified text with hyphens replaced by underscores.
    """
    return slugify(text).replace('-', '_')

def dynamic_model_class_name():
    """
    Returns the name of the dynamic model class or DynamicModel if none is
    provided by the user.
    """
    return settings.DYNAMIC_MODELS.get('DYNAMIC_MODEL_CLASS')

def dynamic_field_class_name():
    """
    Returns the name of the dynamic field class or DynamicField if none is
    provided by the user.
    """
    return settings.DYNAMIC_MODELS.get('DYNAMIC_FIELD_CLASS')

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

def unregister_model(app_label, model_name):
    """
    Deletes a model from Django's app registry. Returns True if the model was
    deleted successfully and False if it was not found.
    """
    try:
        del apps.all_models[app_label][model_name]
    except KeyError:
        return False
    return True

def is_latest_model(model):
    """
    Checks the model hash from the provided model matches the latest hash stored
    in the cache. 
    """
    return cache.get(cache_key(model)) == model._hash

def set_model_hash(model, timeout=60*60*24*3):
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

def check_latest_model(sender, instance, **kwargs):
    """
    Signal handler for dynamic models on pre_save to guard against the
    possibility of a model changing schema between instance instantiation and
    record save.
    """
    if not is_latest_model(sender):
        raise OutdatedModelError(sender)