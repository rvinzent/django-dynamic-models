import pytest
from django.db import connection 
from dynamic_models import signals as dm_signals
from .models import ModelSchema, FieldSchema
from .conftest import db_table_exists, db_table_has_field


def test_subclassed_models_have_base_fields():
    assert ModelSchema._meta.get_field('name')
    assert ModelSchema._meta.get_field('modified')
    assert FieldSchema._meta.get_field('name')
    assert FieldSchema._meta.get_field('data_type')


@pytest.mark.django_db
def test_adding_model_schema_creates_db_table(model_schema):
    assert db_table_exists(model_schema.table_name)


@pytest.mark.django_db
def test_deleting_model_schema_deletes_db_table(model_schema_no_delete):
    table = model_schema_no_delete.table_name
    assert db_table_exists(table)
    model_schema_no_delete.delete()
    assert not db_table_exists(table)


@pytest.mark.django_db
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


@pytest.mark.django_db
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