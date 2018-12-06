import pytest
from django.db.utils import OperationalError
from dynamic_models.utils import db_table_exists
from .models import ModelSchema, FieldSchema

# pylint: disable=unused-argument,invalid-name


def clean_up_model(model_schema):
    _try_destroy(model_schema)
    _try_drop_table(model_schema)

def _try_drop_table(model_schema):
    try:
        model_schema.schema_editor.drop()
    except OperationalError:
        # raised when the table has already been deleted somewhere
        pass

def _try_destroy(model_schema):
    try:
        model_schema.factory.destroy()
    except KeyError: 
        # usually raised when model has been unregistered at another time
        pass

@pytest.fixture
def model_schema(db):
    """Creates and yields an instance of the model schema.

    A database table should be created when it is loaded and cleaned up after
    the test.
    """
    model_schema = ModelSchema.objects.create(name='simple model')
    try:
        yield model_schema
    finally:
        clean_up_model(model_schema)


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
