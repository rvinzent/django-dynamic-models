"""Various utility functions for the dynamic_models app."""
from contextlib import contextmanager
from django.db import connection
from django.conf import settings
from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from . import exceptions


DEFAULT_MAX_LENGTH = 255
DEFAULT_CACHE_KEY_PREFIX = 'dynamic_models_schema_'


def default_fields():
    """Returns the DEFAULT_FIELDS setting."""
    return _settings().get('DEFAULT_FIELDS', {})

def default_max_length():
    """Returns the default max_length value from the settings or 255."""
    return _settings().get('DEFAULT_MAX_LENGTH', DEFAULT_MAX_LENGTH)

def cache_key_prefix():
    return _settings().get('CACHE_KEY_PREFIX', DEFAULT_CACHE_KEY_PREFIX)

def _settings():
    return getattr(settings, 'DYNAMIC_MODELS', {})

def get_registered_model(model_schema):
    """Get a model from Django's app registry."""
    try:
        return apps.get_model(model_schema.app_label, model_schema.model_name)
    except LookupError as err:
        raise exceptions.ModelDoesNotExistError() from err

def is_registered(model):
    apps.clear_cache()
    return model in apps.get_models()

def db_table_exists(table_name):
    """Checks if the table name exists in the database."""
    with _db_cursor() as c:
        return table_name in connection.introspection.table_names(c, table_name)

def db_table_has_field(table_name, field_name):
    """Checks if the table has a given field."""
    table = _get_table_description(table_name)
    return field_name in [field.name for field in table]

def db_field_allows_null(table_name, field_name):
    table_description = _get_table_description(table_name)
    for field in table_description:
        if field.name == field_name:
            return field.null_ok
    raise FieldDoesNotExist(
        'field {} does not exist on table {}'.format(field_name, table_name)
    )

def _get_table_description(table_name):
    with _db_cursor() as c:
        return connection.introspection.get_table_description(c, table_name)

@contextmanager
def _db_cursor():
    """Create a database cursor and close it on exit."""
    cursor = connection.cursor()
    yield cursor
    cursor.close()
