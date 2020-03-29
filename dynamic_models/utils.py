"""Various utility functions for the dynamic_models app."""
import datetime
from contextlib import contextmanager
from django.db import connection
from django.conf import settings
from django.apps import apps
from django.core.cache import cache
from django.core.exceptions import FieldDoesNotExist


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

def receiver_is_connected(receiver_name, signal, sender):
    receivers = signal._live_receivers(sender)
    receiver_strings = [
        "{}.{}".format(r.__module__, r.__name__) for r in receivers
    ]
    return receiver_name in receiver_strings


class LastModifiedCache:

    def cache_key(self, model_schema):
        return cache_key_prefix() + model_schema.db_table

    def get(self, model_schema):
        """Return the last time of modification or the max date value."""
        max_utc = datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)
        return cache.get(self.cache_key(model_schema), max_utc)

    def set(self, model_schema, timestamp, timeout=60*60*24*2):
        cache.set(self.cache_key(model_schema), timestamp, timeout)

    def delete(self, model_schema):
        cache.delete(self.cache_key(model_schema))


class ModelRegistry:
    def __init__(self, app_label):
        self.app_label = app_label

    def is_registered(self, model_name):
        return model_name.lower() in apps.all_models[self.app_label]

    def try_model(self, model_name):
        """Try to return a model from the app registry or None if not found."""
        try:
            return self.get_model(model_name)
        except LookupError:
            return None

    def get_model(self, model_name):
        """Get a model from Django's app registry."""
        return apps.get_model(self.app_label, model_name)

    def unregister_model(self, model_name):
        """Remove a model from the app registry."""
        try:
            del apps.all_models[self.app_label][model_name.lower()]
        except KeyError as err:
            raise LookupError("'{}' not found.".format(model_name)) from err
