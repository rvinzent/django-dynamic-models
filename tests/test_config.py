from django.db import models

from dynamic_models import config


def test_default_fields_setting(settings):
    default_fields = {"default_integer": models.IntegerField()}
    setattr(settings, "DYNAMIC_MODELS", {"DEFAULT_FIELDS": default_fields})
    assert config.default_fields() == default_fields


def test_default_max_length_setting(settings):
    assert config.default_charfield_max_length() != 64
    setattr(settings, "DYNAMIC_MODELS", {"DEFAULT_CHARFIELD_MAX_LENGTH": 64})
    assert config.default_charfield_max_length() == 64


def test_cache_key_prefix(settings):
    assert config.cache_key_prefix() != "test"
    setattr(settings, "DYNAMIC_MODELS", {"CACHE_KEY_PREFIX": "test"})
    assert config.cache_key_prefix() == "test"


def test_cache_timeout(settings):
    assert config.cache_timeout() != 1
    setattr(settings, "DYNAMIC_MODELS", {"CACHE_TIMEOUT": 1})
    assert config.cache_timeout() == 1
