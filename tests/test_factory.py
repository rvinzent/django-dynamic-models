from django.db import models

import pytest

from dynamic_models.factory import FieldFactory, ModelFactory
from dynamic_models.models import FieldSchema


class TestModelFactory:
    def test_get_model_makes_if_not_exists(self, model_registry, model_schema):
        model_registry.unregister_model(model_schema.model_name)
        assert not model_registry.is_registered(model_schema.model_name)
        ModelFactory(model_schema).get_model()
        assert model_registry.is_registered(model_schema.model_name)

    def test_model_has_field_with_field_on_schema(self, model_schema, field_schema):
        model = ModelFactory(model_schema).get_model()
        assert isinstance(model._meta.get_field(field_schema.name), models.IntegerField)

    def test_schema_defines_model_meta(self, model_schema):
        model = ModelFactory(model_schema).get_model()
        assert model.__name__ == model_schema.model_name
        assert model._meta.db_table == model_schema.db_table
        assert model._meta.verbose_name == model_schema.name

    def test_get_model_registers(self, model_registry, model_schema):
        ModelFactory(model_schema).get_model()
        assert model_registry.is_registered(model_schema.model_name)

    def test_destroy_model_unregisters(self, model_registry, model_schema):
        factory = ModelFactory(model_schema)
        factory.get_model()
        assert model_registry.is_registered(model_schema.model_name)
        factory.destroy_model()
        assert not model_registry.is_registered(model_schema.model_name)


class TestFieldFactory:
    @pytest.mark.parametrize(
        "class_name, expected_class, options",
        [
            ("django.db.models.IntegerField", models.IntegerField, {}),
            ("django.db.models.CharField", models.CharField, {"max_length": 255}),
            ("django.db.models.TextField", models.TextField, {}),
            ("django.db.models.FloatField", models.FloatField, {}),
            ("django.db.models.BooleanField", models.BooleanField, {}),
        ],
    )
    def test_make_field(self, class_name, expected_class, options, model_schema):
        field_schema = FieldSchema(
            name="field", class_name=class_name, model_schema=model_schema, kwargs=options
        )
        field = FieldFactory(field_schema).make_field()
        assert isinstance(field, expected_class)

    def test_options_are_passed_to_field(self, model_schema, field_schema):
        field_schema.null = True
        field = FieldFactory(field_schema).make_field()
        assert field.null is True

    @pytest.mark.parametrize(
        "class_name, expected_class, options",
        [
            ("django.db.models.ForeignKey", models.ForeignKey, {"on_delete": models.CASCADE}),
            ("django.db.models.ManyToManyField", models.ManyToManyField, {"blank": True}),
        ],
    )
    def test_table_relationship(
        self, class_name, expected_class, options, model_schema, another_model_schema
    ):
        field_schema = FieldSchema(
            name="field",
            class_name=class_name,
            model_schema=model_schema,
            kwargs={**options, "to": another_model_schema},
        )
        field_schema.null = True
        field = FieldFactory(field_schema).make_field()
        assert isinstance(field, expected_class)
        assert field.null is True
