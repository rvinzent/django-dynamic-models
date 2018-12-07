import pytest
from django.db import models
from dynamic_models import utils


def test_default_fields_setting(settings):
    """Should return a dict of default fields defined in settings."""
    default_fields = {'default_integer': models.IntegerField()}
    setattr(settings, 'DYNAMIC_MODELS', {'DEFAULT_FIELDS': default_fields})
    assert utils.default_fields() == default_fields

def test_default_max_length_setting(settings):
    """Should return the DEFAULT_MAX_LENGTH setting or a default."""
    assert utils.default_max_length() == utils.DEFAULT_MAX_LENGTH
    default_max_length = {'DEFAULT_MAX_LENGTH': 64}
    setattr(settings, 'DYNAMIC_MODELS', default_max_length)
    assert utils.default_max_length() == 64


class TestModelRegistry:
	pass


class TestLastModifiedCache:
	pass