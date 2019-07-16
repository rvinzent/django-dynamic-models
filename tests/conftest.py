import pytest
from django.apps import apps
from django.core.cache import cache
from dynamic_models import utils
from .models import ModelSchema, FieldSchema, ModelFieldSchema

# pylint: disable=unused-argument,invalid-name


TEST_APP_LABEL = 'tests'
MODEL_REGISTRY = utils.ModelRegistry(TEST_APP_LABEL)
STATIC_MODELS = (ModelSchema, FieldSchema, ModelFieldSchema)


def raise_on_save(*args, **kwargs):
    raise AssertionError('save method should not be called')

@pytest.fixture
def prevent_save(monkeypatch):
    monkeypatch.setattr(ModelSchema, 'save', raise_on_save)
    monkeypatch.setattr(FieldSchema, 'save', raise_on_save)
    monkeypatch.setattr(ModelFieldSchema, 'save', raise_on_save)


@pytest.fixture(autouse=True)
def cleanup_cache():
    yield
    cache.clear()

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
