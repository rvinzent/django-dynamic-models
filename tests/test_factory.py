import pytest
from django.db import models
from dynamic_models.factory import ModelFactory, FieldFactory
from dynamic_models.models import ModelFieldSchema
from dynamic_models.utils import db_field_allows_null
from .models import ModelSchema, FieldSchema



@pytest.fixture
def model_schema_no_fields(db, monkeypatch):
    schema = ModelSchema(name='no fields model')

    def get_empty_fields():
        return []

    monkeypatch.setattr(schema, 'get_fields', get_empty_fields)
    return schema


@pytest.fixture
def model_schema_one_field(db, monkeypatch, integer_field_schema):
    schema = ModelSchema(name='one field model')
    model_field_schema = ModelFieldSchema(
        model_schema=schema,
        field_schema=integer_field_schema,
    )

    def get_single_field():
        return [model_field_schema]

    monkeypatch.setattr(schema, 'get_fields', get_single_field)
    return schema


@pytest.fixture
def integer_field_schema(db):
    return FieldSchema(name='integer', data_type='integer')


@pytest.mark.usefixtures('prevent_save')
class TestModelFactory:

    def test_no_field_model_has_base_attributes(self, model_schema_no_fields):
        model = ModelFactory(model_schema_no_fields).make()
        for attr in ('_schema', '_declared', '__module__'):
            assert hasattr(model, attr)

    def test_model_has_field_schema_as_field(self, model_schema_one_field):
        model = ModelFactory(model_schema_one_field).make()
        assert isinstance(model._meta.get_field('integer'), models.IntegerField)

    def test_schema_defines_model_meta(self, model_schema_no_fields):
        model = ModelFactory(model_schema_no_fields).make()
        assert model.__name__ == model_schema_no_fields.model_name
        assert model._meta.db_table == model_schema_no_fields.db_table
        assert model._meta.verbose_name == model_schema_no_fields.name
