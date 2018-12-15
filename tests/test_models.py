import pytest
from dynamic_models import utils
from .models import ModelSchema, FieldSchema

# pylint: disable=redefined-outer-name,invalid-name,unused-argument


@pytest.fixture
def unsaved_model_schema(db):
    return ModelSchema(name='unsaved model')

@pytest.fixture
def model_schema(db):
    return ModelSchema.objects.create(name='simple model')


@pytest.fixture
def model_registry(model_schema):
    return utils.ModelRegistry(model_schema.app_label)


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
