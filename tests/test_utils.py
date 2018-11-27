import pytest
from django.apps import apps
from django.db import models
from dynamic_models import utils
from .conftest import is_registered
from .models import ModelSchema


def test_get_cached_model():
    """
    Should return the model with a given app_label and model_name from Django's
    app registry. Model is reregistered at the end of the test.
    """
    model_name = ModelSchema._meta.model_name
    app_label = ModelSchema._meta.app_label
    assert utils.get_cached_model(app_label, model_name) == ModelSchema
    assert utils.unregister_model(app_label, model_name)
    assert utils.get_cached_model(app_label, model_name) is None
    apps.register_model(app_label, ModelSchema)

def test_unregister_model():
    """
    Should delete the model from the app registry and return it. Model is 
    reregistered at the end of the test.
    """
    model_name = ModelSchema._meta.model_name
    app_label = ModelSchema._meta.app_label
    assert is_registered(ModelSchema)
    assert utils.unregister_model(app_label, model_name)
    assert not is_registered(ModelSchema)
    apps.register_model(app_label, ModelSchema)
    
def test_default_fields_setting(settings):
    """
    Should return a dict of default fields defined in settings.
    """
    default_setting = {'default': models.IntegerField()}
    settings.DYNAMIC_MODELS = {'DEFAULT_FIELDS': default_setting}
    assert utils.default_fields() == default_setting

