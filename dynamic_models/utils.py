"""
Various utility functions for the dynamic models app.
"""
from django.conf import settings
from django.apps import apps
from django.core.cache import cache
from django.utils.text import slugify


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
    return '{}_{}'.format(KEY_PREFIX, model._meta.model_name)

def get_cached_model(app_label, model_name):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        pass

def unregister_model(app_label, model_name):
    try:
        del apps.all_models[app_label][model_name]
    except KeyError:
        return False
    return True

def is_latest_model(model):
    return cache.get(cache_key(model)) == model._hash

def set_model_hash(model):
    cache.set(cache_key(model), model._hash)

def delete_model_hash(model):
    cache.delete(cache_key(model))