import pytest
from django.db import models
from dynamic_models.models import AbstractFieldSchema, DefaultDataTypes

from dynamic_models import exceptions
from .models import ModelSchema, FieldSchema
from .conftest import (
    db_table_exists, db_table_has_field, db_field_allows_null, is_registered
)

# pylint: disable=unused-argument,redefined-outer-name

def test_subclassed_models_have_base_fields():
    assert ModelSchema._meta.get_field('name')
    assert ModelSchema._meta.get_field('modified')
    assert FieldSchema._meta.get_field('name')
    assert FieldSchema._meta.get_field('data_type')

def test_imported_data_types_are_abstract_field_schema_data_types():
    assert DefaultDataTypes == AbstractFieldSchema.DATA_TYPES

def test_adding_model_schema_creates_db_table(model_schema):
    assert db_table_exists(model_schema.table_name)

def test_adding_model_schema_registers_dynamic_model(model_schema):
    assert is_registered(model_schema.as_model())

def test_dynamic_model_is_django_model(model_schema):
    assert issubclass(model_schema.as_model(), models.Model)

def test_deleting_model_schema_deletes_db_table(model_schema_no_delete):
    table = model_schema_no_delete.table_name
    assert db_table_exists(table)
    model_schema_no_delete.delete()
    assert not db_table_exists(table)

def test_deleting_model_schema_unregisters_dynamic_model(model_schema_no_delete):
    model = model_schema_no_delete.as_model()
    assert is_registered(model)
    model_schema_no_delete.delete()
    assert not is_registered(model)

def test_adding_field_schema_adds_db_fields(model_schema, int_field_schema):
    assert not db_table_has_field(
        model_schema.table_name,
        int_field_schema.column_name
    )
    model_schema.add_field(int_field_schema)
    assert db_table_has_field(
        model_schema.table_name,
        int_field_schema.column_name
    )

def test_removing_field_schema_removes_db_fields(model_schema, int_field_schema):
    model_schema.add_field(int_field_schema)
    assert db_table_has_field(
        model_schema.table_name,
        int_field_schema.column_name
    )
    model_schema.remove_field(int_field_schema)
    assert not db_table_has_field(
        model_schema.table_name,
        int_field_schema.column_name
    )

def test_updating_field_updates_db_schema(model_schema, int_field_schema):
    model_schema.add_field(int_field_schema, null=False)
    assert not db_field_allows_null(
        model_schema.table_name,
        int_field_schema.column_name
    )
    model_schema.update_field(int_field_schema, null=True)
    assert db_field_allows_null(
        model_schema.table_name,
        int_field_schema.column_name
    )

def test_char_field_has_settings_default_max_length(settings, model_schema, char_field_schema):
    settings.DYNAMIC_MODELS = {'DEFAULT_MAX_LENGTH': 64}
    field_schema = model_schema.add_field(char_field_schema)
    assert field_schema.as_field().max_length == 64

def test_char_field_max_length_defaults_to_255(model_schema, char_field_schema):
    field_schema = model_schema.add_field(char_field_schema)
    assert field_schema.as_field().max_length == 255

def test_non_char_fields_do_not_have_max_length(model_schema, int_field_schema):
    field = model_schema.add_field(int_field_schema)
    assert field.max_length is None

def test_cannot_change_null_to_not_null(model_schema, int_field_schema):
    null_field = model_schema.add_field(int_field_schema, null=True)
    with pytest.raises(exceptions.NullFieldChangedError,
            match=int_field_schema.column_name):
        null_field.null = False
        null_field.save()

def test_crud_dynamic_models_instances(model_schema, int_field_schema):
    """Dynamic models should be able to create, update, and destroy instances."""
    model_schema.add_field(int_field_schema)
    model = model_schema.as_model()
    field_name = int_field_schema.column_name

    instance = model.objects.create(**{field_name: 1})
    assert instance, "instance not created"

    assert model.objects.get(pk=instance.pk), "instance not retrieved"

    model.objects.update(**{field_name: 2})
    instance.refresh_from_db()
    assert getattr(instance, field_name) == 2, "instance not updated"
    
    pk = instance.pk
    instance.delete()
    with pytest.raises(model.DoesNotExist):
        model.objects.get(pk=pk)

def test_cannot_save_with_outdated_model(model_schema, int_field_schema):
    model = model_schema.as_model()
    model_schema.add_field(int_field_schema, null=True)
    with pytest.raises(exceptions.OutdatedModelError,
            match=model_schema.model_name):
        model.objects.create()
