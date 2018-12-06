import pytest
from .models import ModelSchema, FieldSchema

# pylint: disable=unused-argument,invalid-name


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
