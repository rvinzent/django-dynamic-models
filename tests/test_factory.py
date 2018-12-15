import pytest
from django.db import models
from dynamic_models.factory import ModelFactory, FieldFactory
from dynamic_models.models import ModelFieldSchema
from dynamic_models import utils
from .models import ModelSchema, FieldSchema

# pylint: disable=redefined-outer-name,invalid-name,unused-argument


@pytest.fixture
def model_schema(db, monkeypatch):
    schema = ModelSchema(name='no fields model')

    def get_empty_fields():
        return []

    monkeypatch.setattr(schema, 'get_fields', get_empty_fields)
    return schema


@pytest.fixture
def model_schema_with_field(db, monkeypatch, integer_field_schema):
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


@pytest.fixture
def model_registry(model_schema):
    return utils.ModelRegistry(model_schema.app_label)


@pytest.mark.usefixtures('prevent_save')
class TestModelFactory:

    SCHEMA_CHECKER_RECEIVER = 'dynamic_models.factory.check_model_schema'

    def schema_checker_is_connected(self, model):
        return utils.receiver_is_connected(
            self.SCHEMA_CHECKER_RECEIVER,
            models.signals.pre_save,
            model
        )

    def test_get_model_makes_if_not_exists(self, model_registry, model_schema):
        assert not model_registry.is_registered(model_schema.model_name)
        ModelFactory(model_schema).get_model()
        assert model_registry.is_registered(model_schema.model_name)

    def test_get_model_returns_registered_if_exists(self, monkeypatch, model_registry, model_schema):
        factory = ModelFactory(model_schema)
        model = factory.make()
        assert model_registry.is_registered(model_schema.model_name)

        # prevent future calls to `make` and assume model is current
        monkeypatch.setattr(factory, 'make', lambda: None)
        monkeypatch.setattr(model_schema, 'is_current_model', lambda x: True)
        assert factory.get_model() == model

    def test_model_has_base_attributes(self, model_schema):
        model = ModelFactory(model_schema).make()
        for attr in ('_schema', '_declared', '__module__'):
            assert hasattr(model, attr)

    def test_model_has_field_with_field_on_schema(self, model_schema_with_field):
        model = ModelFactory(model_schema_with_field).make()
        assert isinstance(model._meta.get_field('integer'), models.IntegerField)

    def test_schema_defines_model_meta(self, model_schema):
        model = ModelFactory(model_schema).make()
        assert model.__name__ == model_schema.model_name
        assert model._meta.db_table == model_schema.db_table
        assert model._meta.verbose_name == model_schema.name

    def test_make_model_connects_signals(self, model_schema):
        model = ModelFactory(model_schema).make()
        assert self.schema_checker_is_connected(model)

    def test_make_model_registers(self, model_registry, model_schema):
        ModelFactory(model_schema).make()
        assert model_registry.is_registered(model_schema.model_name)

    def test_destroy_model_disconnects_signal(self, model_schema):
        factory = ModelFactory(model_schema)
        model = factory.make()
        assert self.schema_checker_is_connected(model)
        factory.destroy()
        assert not self.schema_checker_is_connected(model)

    def test_destroy_model_unregisters(self, model_registry, model_schema):
        factory = ModelFactory(model_schema)
        factory.make()
        assert model_registry.is_registered(model_schema.model_name)
        factory.destroy()
        assert not model_registry.is_registered(model_schema.model_name)


@pytest.mark.usefixtures('prevent_save')
class TestFieldFactory:

    @pytest.mark.parametrize('data_type, expected_class, options', [
        ('integer', models.IntegerField, {}),
        ('character', models.CharField, {'max_length': 255}),
        ('text', models.TextField, {}),
        ('float', models.FloatField, {}),
        ('boolean', models.BooleanField, {})
    ])
    def test_make_field(self, data_type, expected_class, options):
        schema = FieldSchema(name='field', data_type=data_type)
        field_schema = ModelFieldSchema(field_schema=schema, **options)
        field = FieldFactory(field_schema).make()
        assert isinstance(field, expected_class)

    def test_options_are_passed_to_field(self):
        schema = FieldSchema(name='field', data_type='integer')
        field_schema = ModelFieldSchema(field_schema=schema, null=True)
        field = FieldFactory(field_schema).make()
        assert field.null is True
