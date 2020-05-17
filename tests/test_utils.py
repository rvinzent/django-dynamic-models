import pytest
from django.core.cache import cache

from dynamic_models.utils import LastModifiedCache


class TestModelRegistry:

    def test_get_model(self, model_schema, model_registry):
        registered_model = model_registry.get_model(model_schema.model_name)
        assert registered_model == model_schema.as_model()
        
    def test_unregister_model(self, model_schema, model_registry):
        registered_model = model_registry.get_model(model_schema.model_name)
        assert registered_model == model_schema.as_model()
        model_registry.unregister_model(model_schema.model_name)

    def test_is_registered(self, model_schema, model_registry):
        assert model_registry.is_registered(model_schema.model_name)
        model_registry.unregister_model(model_schema.model_name)
        assert not model_registry.is_registered(model_schema.model_name)

    def test_unregistering_missing_model_raises_error(self, model_schema, model_registry):
        assert model_registry.is_registered(model_schema.model_name)
        model_registry.unregister_model(model_schema.model_name)
        with pytest.raises(LookupError):
            model_registry.unregister_model(model_schema.model_name)


class TestLastModifiedCache:

    def test_set_last_modified(self, model_schema):
        assert LastModifiedCache().cache_key(model_schema) in cache
        LastModifiedCache().delete(model_schema)
        assert LastModifiedCache().cache_key(model_schema) not in cache
        LastModifiedCache().set(model_schema, model_schema.last_modified)
        assert LastModifiedCache().cache_key(model_schema) in cache

    def test_get_last_modified(self, model_schema):
        assert model_schema.last_modified == LastModifiedCache().get(model_schema)

    def test_delete_last_modified(self, model_schema):
        assert LastModifiedCache().cache_key(model_schema) in cache
        LastModifiedCache().delete(model_schema)
