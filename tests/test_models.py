import pytest
from django.utils import timezone
from dynamic_models import utils
from dynamic_models import exceptions
from .models import ModelSchema, FieldSchema


# pylint: disable=redefined-outer-name,invalid-name,unused-argument


@pytest.mark.django_db
class TestModelSchema:

    def test_is_current_schema_checks_last_modified(self, model_schema):
        assert model_schema.is_current_schema()
        model_schema.last_modified = timezone.now()
        assert not model_schema.is_current_schema()

    def test_is_current_model(self, model_schema, another_model_schema):
        model = model_schema.as_model()
        another_model = another_model_schema.as_model()
        assert model_schema.is_current_model(model)
        with pytest.raises(ValueError):
            model_schema.is_current_model(another_model)

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


class TestFieldSchema:

    def test_cannot_save_with_prohibited_name(self):
        prohibited_name = '__module__'
        with pytest.raises(exceptions.InvalidFieldNameError):
            FieldSchema.objects.create(name=prohibited_name, data_type='integer')

    def test_cannot_change_null_to_not_null(self, model_schema, field_schema):
        model_field = model_schema.add_field(field_schema, null=True)
        with pytest.raises(exceptions.NullFieldChangedError):
            model_field.null = False
            model_field.save()

    def test_related_model_schema_notified_on_update(
            self, model_schema, another_model_schema, field_schema):

        model_schema.add_field(field_schema)
        another_model_schema.add_field(field_schema)

        model = model_schema.as_model()
        another_model = another_model_schema.as_model()

        assert model_schema.is_current_model(model)
        assert another_model_schema.is_current_model(another_model)
        field_schema.update_last_modified()
        assert not model_schema.is_current_model(model)
        assert not another_model_schema.is_current_model(another_model)


@pytest.mark.django_db
class TestDynamicModels:

    @pytest.fixture
    def dynamic_model(self, model_schema, existing_column):
        return model_schema.as_model()

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
        model_schema.name = 'new name'
        model_schema.save()
        with pytest.raises(exceptions.OutdatedModelError):
            dynamic_model.objects.create(field=4)
