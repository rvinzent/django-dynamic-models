from django.apps import apps
from django.core.cache import cache

import pytest

from dynamic_models.models import FieldSchema, ModelSchema
from dynamic_models.utils import ModelRegistry


TEST_APP_LABEL = "dynamic_models"


@pytest.fixture(autouse=True)
def cleanup_cache():
    try:
        yield
    finally:
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
        apps.all_models[TEST_APP_LABEL].clear()
        apps.register_model(TEST_APP_LABEL, ModelSchema)
        apps.register_model(TEST_APP_LABEL, FieldSchema)


@pytest.fixture
def model_registry(model_schema):
    return ModelRegistry(model_schema.app_label)


@pytest.fixture
def unsaved_model_schema(db):
    return ModelSchema(name="unsaved model")


@pytest.fixture
def model_schema(db):
    return ModelSchema.objects.create(name="simple model")


@pytest.fixture
def another_model_schema(db):
    return ModelSchema.objects.create(name="another model")


@pytest.fixture
def field_schema(db, model_schema):
    return FieldSchema.objects.create(
        name="field", class_name="django.db.models.IntegerField", model_schema=model_schema
    )
