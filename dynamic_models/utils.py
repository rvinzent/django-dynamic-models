"""Various utility functions for the dynamic_models app.

`default_fields`     -- return DEFAULT_FIELDS setting
`get_cached_model`   -- return model from app registry
`unregister model`   -- remove model from app registry
`has_current_schema` -- check if model's schema is updated
"""
from django.conf import settings
from django.apps import apps
from . import signals


def default_fields():
    """Returns the DEFAULT_FIELDS setting."""
    try:
        return settings.DYNAMIC_MODELS.get('DEFAULT_FIELDS', {})
    except AttributeError:
        return {}

def get_cached_model(app_label, model_name):
    """Return a model from Django's app registry or None if not found."""
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        pass

def unregister_model(app_label, model_name):
    """Remove a model from Django's app registry.
     
    Also and disconnects any model signals. Returns False if the model was not
    registered and True if it was unregistered successfully.
    """
    try:
        old_model = apps.get_model(app_label, model_name)
        del apps.all_models[app_label][model_name]
    except (KeyError, LookupError):
        return False
    signals.disconnect_dynamic_model(old_model)
    return True

def has_current_schema(schema, model):
    """Check that model's schema is up-to-date."""
    return schema.modified < model._declared
