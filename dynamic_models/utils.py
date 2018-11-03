"""
Various utility functions for the dynamic models app.
"""
from django.utils.text import slugify
from django.conf import settings


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
    return settings.DYNAMIC_MODELS.get(
        'DYNAMIC_MODEL_CLASS',
        'dynamic_models.DynamicModel'
    )

def dynamic_field_class_name():
    """
    Returns the name of the dynamic field class or DynamicField if none is
    provided by the user.
    """
    return settings.DYNAMIC_MODELS.get(
        'DYNAMIC_FIELD_CLASS',
        'dynamic_models.DynamicField'
    )

def default_fields():
    """
    Returns the DEFAULT_FIELDS setting.
    """
    return settings.DYNAMIC_MODELS.get('DEFAULT_FIELDS', {})
