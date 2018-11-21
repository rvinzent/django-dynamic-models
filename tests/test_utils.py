import pytest
from django.apps import apps
from django.db import models
from dynamic_models import utils


def test_get_cached_model(model_schema):
    model = model_schema.get_dynamic_model()
    model_name = model._meta.model_name
    app_label = model._meta.app_label
    assert utils.get_cached_model(app_label, model_name) == model
    utils.unregister_model(app_label, model_name)
    assert utils.get_cached_model(app_label, model_name) is None

def test_unregister_model(model_schema):
    model = model_schema.get_dynamic_model()
    model_name = model._meta.model_name
    app_label = model._meta.app_label
    assert model_name in apps.all_models[app_label]
    utils.unregister_model(model._meta.model_name, model._meta.app_label)
    assert not model_name in apps.all_models[app_label]
    # register the model again to avoid any errors on delete
    apps.register_model(app_label, model)
    
def test_default_fields_setting(settings):
    default_setting = {'default': models.IntegerField()}
    settings.DYNAMIC_MODELS = {'DEFAULT_FIELDS': default_setting}
    assert utils.default_fields() == default_setting

