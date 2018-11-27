import pytest
from contextlib import contextmanager
from django.db import connection
from django.apps import apps
from .models import ModelSchema, FieldSchema


def is_registered(model):
    apps.clear_cache()
    return model in apps.get_models()

@contextmanager
def _db_cursor():
    """
    Create a database cursor and close it on exit.
    """
    cursor = connection.cursor()
    yield cursor
    cursor.close()

def db_table_exists(table_name):
    """
    Checks if the table name exists in the database.
    """
    with _db_cursor() as c:
        return table_name in connection.introspection.table_names(c, table_name)

def db_table_has_field(table_name, field_name):
    """
    Checks if the table has a given field.
    """
    with _db_cursor() as c:
        desc = connection.introspection.get_table_description(c, table_name)
        return field_name in [field.name for field in desc]