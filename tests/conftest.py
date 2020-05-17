import pytest
from django.apps import apps
from django.core.cache import cache
from dynamic_models import utils
from dynamic_models.models import ModelFieldSchema
from tests.models import ModelSchema, FieldSchema

# pylint: disable=unused-argument,invalid-name


TEST_APP_LABEL = 'tests'
MODEL_REGISTRY = utils.ModelRegistry(TEST_APP_LABEL)
STATIC_MODELS = (ModelSchema, FieldSchema)


@pytest.fixture
def prevent_save(monkeypatch):
    monkeypatch.setattr(ModelSchema, 'save', raise_on_save)
    monkeypatch.setattr(FieldSchema, 'save', raise_on_save)
    monkeypatch.setattr(ModelFieldSchema, 'save', raise_on_save)


def raise_on_save(*args, **kwargs):
    raise AssertionError('save method should not be called')


@pytest.fixture(autouse=True)
def cleanup_cache():
    yield
    cache.clear()


@pytest.fixture
def model_registry(model_schema):
    return utils.ModelRegistry(model_schema.app_label)


@pytest.fixture(autouse=True)
def cleanup_registry():
    """
    The app registry bleeds between tests. This fixture removes all dynamically
    declared models after each test.
    """
    try:
        yield
    finally:
        test_app_config = apps.get_app_config(TEST_APP_LABEL)
        registered_models = test_app_config.get_models()
        models_to_remove = [
            model for model in registered_models if model not in STATIC_MODELS
        ]
        for model in models_to_remove:
            MODEL_REGISTRY.unregister_model(model.__name__)


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
def another_model_schema(db):
    return ModelSchema.objects.create(name='another model')


@pytest.fixture
def field_schema(db):
    return FieldSchema.objects.create(name='field', data_type='integer')


@pytest.fixture
def existing_column(db, model_schema, field_schema):
    model_schema.add_field(field_schema)
