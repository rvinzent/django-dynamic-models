import pytest
from django.db import connection 
from .models import SimpleModelSchema, SimpleFieldSchema, RelatedModel
from dynamic_models import signals as dm_signals

@pytest.fixture(scope='module')
def related_instance(db):
    """
    Returns a related model instance.
    """
    return RelatedModel.objects.create(name='related')

@pytest.fixture
def model_schema_instance(db, related_instance):
    """
    Creates and yields an instance of the model schema. A database table should
    be created when it is created and cleaned up with the instance is deleted.
    """
    instance = SimpleModelSchema.objects.create(
        name='simple model',
        normal_field=1,
        related_field=related_instance
    )
    yield instance
    instance.delete()

@pytest.fixture
def field_schema_instance(db, related_instance):
    return SimpleFieldSchema.objects.create(
        name='simple',
        data_type=SimpleFieldSchema.DATA_TYPES.char,
        normal_field=1,
        related_field=related_instance
    )
    

def db_table_exists(table_name):
    """
    Checks if the table name exists in the database.
    """
    return table_name in connection.instrospection.table_names()

def db_table_has_column(table_name, column_name):
    return 
    

def test_subclassed_models_have_base_attributes():
    assert hasattr(SimpleModelSchema, 'name')
    assert hasattr(SimpleModelSchema, '_fields')
    assert hasattr(SimpleFieldSchema, 'name')
    assert hasattr(SimpleFieldSchema, 'data_type')

@pytest.mark.django_db
def test_adding_schema_model_creates_db_tables(model_schema_instance):
    assert db_table_exists(model_schema_instance.table_name)

@pytest.mark.django_db
def test_adding_fields_to_schema_model_adds_db_fields(
    model_schema_instance,
    field_schema_instance):
    assert False
