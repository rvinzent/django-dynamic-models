import pytest
from django.db import connection, models
from dynamic_models import signals as dm_signals

from dynamic_models import exceptions
from .models import ModelSchema, FieldSchema
from .conftest import db_table_exists, db_table_has_field, is_registered



@pytest.fixture
def model_schema(request, db):
    """
    Creates and yields an instance of the model schema. A database table should
    be created when it is loaded and cleaned up after the test.
    """
    instance = ModelSchema.objects.create(name='simple model')
    request.addfinalizer(instance.delete)
    return instance

@pytest.fixture
def model_schema_no_delete(db):
    """
    Creates a model schema instance that must be manually cleaned up. Use this
    to test for correct table deletion.
    """
    return ModelSchema.objects.create(name='simple model')

@pytest.fixture
def int_field_schema(db):
    """
    Creates an integer field schema instance. Should not add a column to any
    table until it is added to a model schema instance with
    model_schema.add_field.
    """
    return FieldSchema.objects.create(
        name='simple integer',
        data_type=FieldSchema.DATA_TYPES.int
    )

@pytest.fixture
def char_field_schema(db):
    """
    Creates an char field schema instance. Should not add a column to any
    table until it is added to a model schema instance with
    model_schema.add_field.
    """
    return FieldSchema.objects.create(
        name='simple character',
        data_type=FieldSchema.DATA_TYPES.char
    )


def test_subclassed_models_have_base_fields():
    assert ModelSchema._meta.get_field('name')
    assert ModelSchema._meta.get_field('modified')
    assert FieldSchema._meta.get_field('name')
    assert FieldSchema._meta.get_field('data_type')

@pytest.mark.django_db
def test_adding_model_schema_creates_db_table(model_schema):
    assert db_table_exists(model_schema.table_name)

@pytest.mark.django_db
def test_adding_model_schema_registers_dynamic_model(model_schema):
    assert is_registered(model_schema.get_dynamic_model())

@pytest.mark.django_db
def test_dynamic_model_is_django_model(model_schema):
    assert issubclass(model_schema.get_dynamic_model(), models.Model)

@pytest.mark.django_db
def test_deleting_model_schema_deletes_db_table(model_schema_no_delete):
    table = model_schema_no_delete.table_name
    assert db_table_exists(table)
    model_schema_no_delete.delete()
    assert not db_table_exists(table)

@pytest.mark.db
def test_deleting_model_unregisters(model_schema_no_delete):
    model = model_schema_no_delete.get_dynamic_model()
    assert is_registered(model)
    model_schema_no_delete.delete()
    assert not is_registered(model)

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

@pytest.mark.django_db
def test_char_field_requires_max_length(model_schema, char_field_schema):
    with pytest.raises(exceptions.InvalidFieldError,
            match=char_field_schema.column_name):
        model_schema.add_field(char_field_schema)
    assert model_schema.add_field(char_field_schema, max_length=64)

@pytest.mark.django_db
def test_non_char_fields_cannot_have_max_length(model_schema, int_field_schema):
    with pytest.raises(exceptions.InvalidFieldError,
            match=int_field_schema.column_name):
        model_schema.add_field(int_field_schema, max_length=64)

@pytest.mark.django_db
def test_cannot_change_null_to_not_null(model_schema, int_field_schema):
    null_field = model_schema.add_field(int_field_schema, required=False)
    with pytest.raises(exceptions.NullFieldChangedError,
            match=int_field_schema.column_name):
        null_field.required = True
        null_field.save()

@pytest.mark.django_db
def test_schema_timestamp_updated_on_field_change(model_schema, int_field_schema):
    field = model_schema.add_field(int_field_schema, required=True)
    initial_time = model_schema.modified
    field.required = False
    field.save()
    model_schema.refresh_from_db()
    assert model_schema.modified > initial_time 

@pytest.mark.django_db
def test_CRUD_dynamic_models_instances(model_schema, int_field_schema):
    model_schema.add_field(int_field_schema)
    model = model_schema.get_dynamic_model()
    field_name = int_field_schema.column_name

    instance = model.objects.create(**{field_name: 1})
    assert instance, "instance not created"
    
    model.objects.update(**{field_name: 2})
    instance.refresh_from_db()
    assert getattr(instance, field_name) == 2, "instance not updated"
    
    pk = instance.pk
    instance.delete()
    with pytest.raises(model.DoesNotExist):
        model.objects.get(pk=pk)


@pytest.mark.django_db
def test_cannot_save_with_outdated_model(model_schema, int_field_schema):
    model = model_schema.get_dynamic_model()
    model_schema.add_field(int_field_schema, required=False)
    with pytest.raises(exceptions.OutdatedModelError,
            match=model_schema.model_name):
        model.objects.create()
