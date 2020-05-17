"""Various utility functions for the dynamic_models app."""
import datetime
from contextlib import contextmanager
from django.db import connection
from django.conf import settings
from django.apps import apps
from django.core.cache import cache
from django.core.exceptions import FieldDoesNotExist

from dynamic_models import config


def db_table_exists(table_name):
    """Checks if the table name exists in the database."""
    with _db_cursor() as c:
        table_names = connection.introspection.table_names(c)
        return table_name in table_names


def db_table_has_field(table_name, field_name):
    """Checks if the table has a given field."""
    table = _get_table_description(table_name)
    return field_name in [field.name for field in table]


def db_field_allows_null(table_name, field_name):
    table_description = _get_table_description(table_name)
    for field in table_description:
        if field.name == field_name:
            return field.null_ok
    raise FieldDoesNotExist(f'field {field_name} does not exist on table {table_name}')



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
        "{}.{}".format(r.__module__, r.__name__)
        for r in receivers
    ]
    return receiver_name in receiver_strings


class LastModifiedCache:

    def cache_key(self, model_schema):
        return config.cache_key_prefix() + model_schema.db_table

    def get(self, model_schema):
        """Return the last time of modification or the max date value."""
        max_date = datetime.datetime.max
        if settings.USE_TZ:
            max_date = max_date.replace(tzinfo=datetime.timezone.utc)
        return cache.get(self.cache_key(model_schema), max_date)

    def set(self, model_schema, timestamp, timeout=config.cache_timeout()):
        cache.set(self.cache_key(model_schema), timestamp, timeout)

    def delete(self, model_schema):
        cache.delete(self.cache_key(model_schema))


class ModelRegistry:
    def __init__(self, app_label):
        self.app_label = app_label

    def is_registered(self, model_name):
        return model_name.lower() in apps.all_models[self.app_label]

    def get_model(self, model_name):
        try:
            return apps.get_model(self.app_label, model_name)
        except LookupError:
            return None

    def unregister_model(self, model_name):
        try:
            del apps.all_models[self.app_label][model_name.lower()]
        except KeyError as err:
            raise LookupError("'{}' not found.".format(model_name)) from err
