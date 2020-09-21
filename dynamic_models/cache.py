from django.core.cache import cache
from django.utils import timezone

from dynamic_models import config


def cache_key(model_name):
    return config.cache_key_prefix() + model_name.lower()


def get_last_modified(model_name):
    return cache.get(cache_key(model_name))


def update_last_modified(model_name, timeout=config.cache_timeout()):
    cache.set(cache_key(model_name), timezone.now(), timeout)


def clear_last_modified(model_name):
    cache.delete(cache_key(model_name))
