from django.utils import timezone

import pytest

from dynamic_models import cache


TEST_MODEL_NAME = "test"
now = timezone.now()


@pytest.fixture
def mock_now(monkeypatch):
    monkeypatch.setattr(timezone, "now", lambda: now)


def test_get_and_update_last_modified(mock_now):
    assert cache.get_last_modified(TEST_MODEL_NAME) is None
    cache.update_last_modified(TEST_MODEL_NAME)
    assert cache.get_last_modified(TEST_MODEL_NAME) == now


def test_delete_last_modified(mock_now):
    cache.update_last_modified(TEST_MODEL_NAME)
    assert cache.get_last_modified(TEST_MODEL_NAME) == now
    cache.clear_last_modified(TEST_MODEL_NAME)
    assert cache.get_last_modified(TEST_MODEL_NAME) is None
