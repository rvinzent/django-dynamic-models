import pytest


@pytest.fixture
def unsaved_model_schema():
    return ModelSchema(name='unsaved model')