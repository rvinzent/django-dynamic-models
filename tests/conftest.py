import pytest
from dynamic_models.models import ModelFieldSchema
from .models import ModelSchema, FieldSchema

# pylint: disable=unused-argument,invalid-name

def raise_on_save(*args, **kwargs):
    raise AssertionError('save method should not be called')

@pytest.fixture
def prevent_save(monkeypatch):
    monkeypatch.setattr(ModelSchema, 'save', raise_on_save)
    monkeypatch.setattr(FieldSchema, 'save', raise_on_save)
    monkeypatch.setattr(ModelFieldSchema, 'save', raise_on_save)
