import pytest
from django.db import connection 
from dynamic_models import signals as dm_signals
from .models import SimpleModelSchema, SimpleFieldSchema


@pytest.fixture
def model_schema(db):
    """
    Creates and yields an instance of the model schema. A database table should
    be created when it is loaded and cleaned up after the test.
    """
    instance = SimpleModelSchema.objects.create(
        name='simple model',
        extra_field=1
    )
    yield instance
    instance.delete()

@pytest.fixture
def model_schema_no_delete(db):
    """
    Creates a model schema instance that must be manually cleaned up. Use this
    to test for correct table deletion.
    """
    return SimpleModelSchema.objects.create(name='simple model', extra_field=1)

@pytest.fixture
def field_schema(db):
    """
    Creates a field schema instance. Should
    not add a column to any table until it is added to a model schema instance
    with model_schema.add_field
    """
    return SimpleFieldSchema.objects.create(
        name='simple',
        data_type=SimpleFieldSchema.DATA_TYPES.char,
        normal_field=1
    )

def db_table_exists(table_name):
    """
    Checks if the table name exists in the database.
    """
    return table_name in connection.instrospection.table_names()

def db_table_has_field(table_name, field_name):
    """
    Checks if the table has a given field.
    """
    description = connection.instrospection.get_table_description(table_name)
    assert field_name in (field.name for field in description)

def test_subclassed_models_have_base_attributes():
    assert getattr(SimpleModelSchema, 'name', None)
    assert getattr(SimpleModelSchema, '_fields', None)
    assert getattr(SimpleFieldSchema, 'name', None)
    assert getattr(SimpleFieldSchema, 'data_type', None)

@pytest.mark.django_db
def test_adding_schema_model_creates_db_table(model_schema):
    assert db_table_exists(model_schema.table_name)

@pytest.mark.django_db
def test_deleting_schema_model_deletes_db_table(model_schema_no_delete):
    table = model_schema.table_name
    assert db_table_exists(table)
    model_schema.delete()
    assert not db_table_exists(table)

@pytest.mark.django_db
def test_adding_fields_to_schema_model_adds_db_fields(model_schema, field_schema):
    assert not db_table_has_field(
        model_schema.table_name,
        field_schema.column_name
    )
    model_schema.add_field(field_schema)
    assert db_table_has_field(
        model_schema.table_name,
        field_schema.column_name
    )

@pytest.mark.django_db
def test_removing_fields_from_schema_removes_db_fields(model_schema, field_schema):
    model_schema.add_field(field_schema)
    assert db_table_has_field(
        model_schema.table_name,
        field_shema.column_name
    )
    model_schema.remove_field(field_schema)
    assert not db_table_has_field(
        model_schema.table_name,
        field_schema.column_name
    )