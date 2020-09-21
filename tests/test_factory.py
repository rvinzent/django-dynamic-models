import pytest
from django.db import models
from dynamic_models.factory import ModelFactory, FieldFactory
from dynamic_models.utils import receiver_is_connected
from dynamic_models.models import FieldSchema


class TestModelFactory:
    def schema_checker_is_connected(self, model):
        return receiver_is_connected(
            "dynamic_models.factory.check_model_schema", models.signals.pre_save, model
        )

    def test_get_model_makes_if_not_exists(self, model_registry, model_schema):
        model_registry.unregister_model(model_schema.model_name)
        assert not model_registry.is_registered(model_schema.model_name)
        ModelFactory(model_schema).get_model()
        assert model_registry.is_registered(model_schema.model_name)

    def test_get_model_returns_registered_if_exists(
        self, monkeypatch, model_registry, model_schema
    ):
        factory = ModelFactory(model_schema)
        model = factory.make_model()
        assert model_registry.is_registered(model_schema.model_name)
        assert factory.get_model() is model

    def test_model_has_base_attributes(self, model_schema):
        model = ModelFactory(model_schema).make_model()
        for attr in ("_declared", "__module__"):
            assert hasattr(model, attr)

    def test_model_has_field_with_field_on_schema(self, model_schema, field_schema):
        model = ModelFactory(model_schema).make_model()
        assert isinstance(model._meta.get_field(field_schema.name), models.IntegerField)

    def test_schema_defines_model_meta(self, model_schema):
        model = ModelFactory(model_schema).make_model()
        assert model.__name__ == model_schema.model_name
        assert model._meta.db_table == model_schema.db_table
        assert model._meta.verbose_name == model_schema.name

    def test_make_model_connects_signals(self, model_schema):
        model = ModelFactory(model_schema).make_model()
        assert self.schema_checker_is_connected(model)

    def test_make_model_registers(self, model_registry, model_schema):
        ModelFactory(model_schema).make_model()
        assert model_registry.is_registered(model_schema.model_name)

    def test_destroy_model_disconnects_signal(self, model_schema):
        factory = ModelFactory(model_schema)
        model = factory.make_model()
        assert self.schema_checker_is_connected(model)
        factory.destroy_model()
        assert not self.schema_checker_is_connected(model)

    def test_destroy_model_unregisters(self, model_registry, model_schema):
        factory = ModelFactory(model_schema)
        factory.make_model()
        assert model_registry.is_registered(model_schema.model_name)
        factory.destroy_model()
        assert not model_registry.is_registered(model_schema.model_name)


class TestFieldFactory:
    @pytest.mark.parametrize(
        "data_type, expected_class, options",
        [
            ("integer", models.IntegerField, {}),
            ("character", models.CharField, {"max_length": 255}),
            ("text", models.TextField, {}),
            ("float", models.FloatField, {}),
            ("boolean", models.BooleanField, {}),
        ],
    )
    def test_make_field(self, data_type, expected_class, options, model_schema):
        field_schema = FieldSchema(name="field", data_type=data_type, model_schema=model_schema)
        field = FieldFactory(field_schema).make_field()
        assert isinstance(field, expected_class)

    def test_options_are_passed_to_field(self, model_schema, field_schema):
        field_schema.null = True
        field = FieldFactory(field_schema).make_field()
        assert field.null is True
