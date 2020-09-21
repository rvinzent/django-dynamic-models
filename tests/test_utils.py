import pytest


def test_get_model(model_schema, model_registry):
    registered_model = model_registry.get_model(model_schema.model_name)
    assert registered_model == model_schema.as_model()


def test_unregister_model(model_schema, model_registry):
    registered_model = model_registry.get_model(model_schema.model_name)
    assert registered_model == model_schema.as_model()
    model_registry.unregister_model(model_schema.model_name)


def test_is_registered(model_schema, model_registry):
    assert model_registry.is_registered(model_schema.model_name)
    model_registry.unregister_model(model_schema.model_name)
    assert not model_registry.is_registered(model_schema.model_name)


def test_unregistering_missing_model_raises_error(model_schema, model_registry):
    assert model_registry.is_registered(model_schema.model_name)
    model_registry.unregister_model(model_schema.model_name)
    with pytest.raises(LookupError):
        model_registry.unregister_model(model_schema.model_name)
