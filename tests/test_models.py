import pytest
from django.db import models
from dynamic_models import cache, utils
from dynamic_models.exceptions import (
    InvalidFieldNameError,
    NullFieldChangedError,
    OutdatedModelError,
)
from dynamic_models.models import FieldSchema


class TestModelSchema:
    def test_is_current_model(self, model_schema):
        model = model_schema.as_model()
        assert utils.is_current_model(model)
        cache.update_last_modified(model_schema.model_name)
        assert not utils.is_current_model(model)

    def test_model_is_registered_on_create(self, model_registry, unsaved_model_schema):
        assert not model_registry.is_registered(unsaved_model_schema.model_name)
        unsaved_model_schema.save()
        assert model_registry.is_registered(unsaved_model_schema.model_name)

    def test_model_table_is_created_on_create(self, unsaved_model_schema):
        table_name = unsaved_model_schema.db_table
        assert not utils.db_table_exists(table_name)
        unsaved_model_schema.save()
        assert utils.db_table_exists(table_name)

    def test_model_registry_is_updated_on_update(self, model_registry, model_schema):
        assert model_registry.is_registered("SimpleModel")
        assert not model_registry.is_registered("NewName")
        model_schema.name = "new name"
        model_schema.save()
        assert not model_registry.is_registered("SimpleModel")
        assert model_registry.is_registered("NewName")

    def test_model_table_is_updated_on_update(self, model_schema):
        assert utils.db_table_exists("dynamic_models_simple_model")
        assert not utils.db_table_exists("dynamic_models_new_name")
        model_schema.name = "new name"
        model_schema.save()
        assert utils.db_table_exists("dynamic_models_new_name")
        assert not utils.db_table_exists("dynamic_models_simple_model")

    def test_model_table_is_dropped_on_delete(self, model_schema):
        assert utils.db_table_exists(model_schema.db_table)
        model_schema.delete()
        assert not utils.db_table_exists(model_schema.db_table)

    def test_model_is_unregistered_on_delete(self, model_registry, model_schema):
        assert model_registry.is_registered(model_schema.model_name)
        model_schema.delete()
        assert not model_registry.is_registered(model_schema.model_name)

    def test_add_field_creates_column(self, model_schema):
        field_schema = FieldSchema(
            name="special", class_name="django.db.models.IntegerField", model_schema=model_schema
        )
        table_name = model_schema.db_table
        column_name = field_schema.db_column
        assert not utils.db_table_has_field(table_name, column_name)
        field_schema.save()
        assert utils.db_table_has_field(table_name, column_name)

    def test_update_field_updates_column(self, model_schema, field_schema):
        table_name = model_schema.db_table
        column_name = field_schema.db_column
        assert not utils.db_field_allows_null(table_name, column_name)
        field_schema.null = True
        field_schema.save()
        assert utils.db_field_allows_null(table_name, column_name)

    def test_deleting_field_drops_column(self, model_schema, field_schema):
        table_name = model_schema.db_table
        column_name = field_schema.db_column
        assert utils.db_table_has_field(table_name, column_name)
        field_schema.delete()
        assert not utils.db_table_has_field(table_name, column_name)


class TestFieldSchema:
    def test_cannot_save_with_prohibited_name(self, model_schema):
        prohibited_name = "__module__"
        with pytest.raises(InvalidFieldNameError):
            FieldSchema.objects.create(
                name=prohibited_name, class_name="django.db.models.IntegerField", model_schema=model_schema
            )

    def test_cannot_change_null_to_not_null(self, model_schema):
        null_field = FieldSchema.objects.create(
            name="field",
            class_name="django.db.models.IntegerField",
            model_schema=model_schema,
            kwargs={"null": True},
        )
        with pytest.raises(NullFieldChangedError):
            null_field.null = False
            null_field.save()

    def test_related_model_schema_notified_on_field_update(self, model_schema, field_schema):
        model = model_schema.as_model()
        assert utils.is_current_model(model)
        field_schema.update_last_modified()
        assert not utils.is_current_model(model)


@pytest.fixture
def dynamic_model(model_schema, field_schema):
    return model_schema.as_model()


@pytest.mark.django_db
class TestDynamicModels:
    def test_can_create(self, dynamic_model):
        assert dynamic_model.objects.create(field=2)

    def test_can_get(self, dynamic_model):
        obj = dynamic_model.objects.create(field=-3)
        assert dynamic_model.objects.get(pk=obj.pk)

    def test_can_update(self, dynamic_model):
        obj = dynamic_model.objects.create(field=4)
        dynamic_model.objects.filter(pk=obj.pk).update(field=6)
        obj.refresh_from_db()
        assert obj.field == 6

    def test_can_delete(self, dynamic_model):
        obj = dynamic_model.objects.create(field=3)
        obj.delete()
        with pytest.raises(dynamic_model.DoesNotExist):
            dynamic_model.objects.get(pk=obj.pk)

    def test_cannot_save_with_outdated_model(self, model_schema, dynamic_model):
        model_schema.name = "new name"
        model_schema.save()
        with pytest.raises(OutdatedModelError):
            dynamic_model.objects.create(field=4)

    def test_model_with_foreign_key(self, model_schema, another_model_schema):
        FieldSchema.objects.create(
            name="related",
            model_schema=model_schema,
            class_name="django.db.models.ForeignKey",
            kwargs={
                "to": another_model_schema.model_name,
                "on_delete": models.CASCADE,
                "related_name": "parent_objects",
            }
        )
        model = model_schema.as_model()
        related_model = another_model_schema.as_model()

        related_instance = related_model.objects.create()
        model_instance = model.objects.create(related=related_instance)

        assert model_instance.related == related_instance
        assert related_instance.parent_objects.first() == model_instance

    def test_model_with_many_to_many(self, model_schema, another_model_schema):
        FieldSchema.objects.create(
            name="many_related",
            model_schema=model_schema,
            class_name="django.db.models.ManyToManyField",
            kwargs={"to": another_model_schema.model_name, "related_name": "related_objects"},
        )
        model = model_schema.as_model()
        related_model = another_model_schema.as_model()

        model_instance = model.objects.create()
        related_model_instance = related_model.objects.create()
        model_instance.many_related.add(related_model_instance)

        assert model_instance.many_related.first() == related_model_instance
        assert related_model_instance.related_objects.first() == model_instance
