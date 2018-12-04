import pytest
from contextlib import contextmanager
from django.db import connection
from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from .models import ModelSchema, FieldSchema


@pytest.fixture
def model_schema(request, db):
    """Creates and yields an instance of the model schema.

    A database table should be created when it is loaded and cleaned up after
    the test.
    """
    instance = ModelSchema.objects.create(name='simple model')
    try:
        yield instance
    finally:
        instance.delete()

@pytest.fixture
def model_schema_no_delete(db):
    """Creates a model schema instance that must be manually cleaned up.

    Use this fixture to test for correct deletion behavior.
    """
    return ModelSchema.objects.create(name='simple model')

@pytest.fixture
def int_field_schema(db):
    """Creates an integer field schema instance.

    Fixture does not add a column to any table until it is added to a model
    schema instance with the `model_schema.add_field` method.
    """
    return FieldSchema.objects.create(
        name='simple integer',
        data_type=FieldSchema.DATA_TYPES.int
    )

@pytest.fixture
def char_field_schema(db):
    """Creates field schema instance with the character data type.

    Fixture does not add a column to any table until it is added to a model
    schema instance with the `model_schema.add_field` method.
    """
    return FieldSchema.objects.create(
        name='simple character',
        data_type=FieldSchema.DATA_TYPES.char
    )

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

def _get_table_description(table_name):
    with _db_cursor() as c:
        return connection.introspection.get_table_description(c, table_name)

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
    table_description = _get_table_description(table_name)
    return field_name in [field.name for field in table_description]

def db_field_allows_null(table_name, field_name):
    table_description = _get_table_description(table_name)
    for field in table_description:
        if field.name == field_name:
            return field.null_ok
    raise FieldDoesNotExist(
        'field {} does not exist on table {}'.format(field_name, table_name)
    )
