import pytest
from dynamic_models import utils
from .models import ModelSchema, FieldSchema


# pylint: disable=redefined-outer-name,invalid-name,unused-argument


@pytest.fixture
def model_registry(model_schema):
    return utils.ModelRegistry(model_schema.app_label)

@pytest.fixture
def unsaved_model_schema(db):
    return ModelSchema(name='unsaved model')

@pytest.fixture
def model_schema(db):
    return ModelSchema.objects.create(name='simple model')

@pytest.fixture
def field_schema(db):
    return FieldSchema.objects.create(name='field', data_type='integer')

@pytest.fixture
def existing_column(db, model_schema, field_schema):
    model_schema.add_field(field_schema)


@pytest.mark.django_db
class TestModelSchema:

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
        assert model_registry.is_registered('SimpleModel')
        assert not model_registry.is_registered('NewName')
        model_schema.name = 'new name'
        model_schema.save()
        assert not model_registry.is_registered('SimpleModel')
        assert model_registry.is_registered('NewName')

    def test_model_table_is_updated_on_update(self, model_schema):
        assert utils.db_table_exists('tests_simple_model')
        assert not utils.db_table_exists('tests_new_name')
        model_schema.name = 'new name'
        model_schema.save()
        assert utils.db_table_exists('tests_new_name')
        assert not utils.db_table_exists('tests_simple_model')

    def test_model_table_is_dropped_on_delete(self, model_schema):
        assert utils.db_table_exists(model_schema.db_table)
        model_schema.delete()
        assert not utils.db_table_exists(model_schema.db_table)

    def test_model_is_unregistered_on_delete(self, model_registry, model_schema):
        assert model_registry.is_registered(model_schema.model_name)
        model_schema.delete()
        assert not model_registry.is_registered(model_schema.model_name)

    def test_add_field_creates_column(self, model_schema, field_schema):
        table_name = model_schema.db_table
        column_name = field_schema.db_column
        assert not utils.db_table_has_field(table_name, column_name)
        model_schema.add_field(field_schema)
        assert utils.db_table_has_field(table_name, column_name)

    @pytest.mark.usefixtures('existing_column')
    def test_update_field_updates_column(self, model_schema, field_schema):
        table_name = model_schema.db_table
        column_name = field_schema.db_column
        assert not utils.db_field_allows_null(table_name, column_name)
        model_schema.update_field(field_schema, null=True)
        assert utils.db_field_allows_null(table_name, column_name)

    @pytest.mark.usefixtures('existing_column')
    def test_remove_field_drops_column(self, model_schema, field_schema):
        table_name = model_schema.db_table
        column_name = field_schema.db_column
        assert utils.db_table_has_field(table_name, column_name)
        model_schema.remove_field(field_schema)
        assert not utils.db_table_has_field(table_name, column_name)
