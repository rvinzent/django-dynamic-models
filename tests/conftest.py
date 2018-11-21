import pytest
from django.db import connection
from .models import ModelSchema, FieldSchema


@pytest.fixture
def model_schema(request, db):
    """
    Creates and yields an instance of the model schema. A database table should
    be created when it is loaded and cleaned up after the test.
    """
    instance = ModelSchema.objects.create(name='simple model')
    request.addfinalizer(instance.delete)
    return instance

@pytest.fixture
def model_schema_no_delete(db):
    """
    Creates a model schema instance that must be manually cleaned up. Use this
    to test for correct table deletion.
    """
    return ModelSchema.objects.create(name='simple model')

@pytest.fixture
def int_field_schema(db):
    """
    Creates a field schema instance. Should
    not add a column to any table until it is added to a model schema instance
    with model_schema.add_field
    """
    return FieldSchema.objects.create(
        name='simple integer',
        data_type=FieldSchema.DATA_TYPES.int
    )

@pytest.fixture
def char_field_schema(db):
    return FieldSchema.objects.create(
        name='simple character',
        data_type=FieldSchema.DATA_TYPES.char
    )

def db_table_exists(table_name):
    """
    Checks if the table name exists in the database.
    """
    return table_name in connection.introspection.table_names()

def db_table_has_field(table_name, field_name):
    """
    Checks if the table has a given field.
    """
    description = connection.introspection.get_table_description(table_name)
    assert field_name in (field.name for field in description)