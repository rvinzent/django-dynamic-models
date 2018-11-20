"""
Settings for testing against a postgres backend.
"""
# pylint: disable=W0614, W0401
from decouple import config
from .base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DYNAMIC_MODELS_DB', default='dynamic_models'),
        'USER': config('DYNAMIC_MODELS_DB_USER', default='dynamic_models'),
        'PASSWORD': config('DYNAMIC_MODELS_DB_PASSWORD', default=''),
        'HOST': config('DYNAMIC_MODELS_POSTGRES_HOST', default='127.0.0.1'),
        'PORT': config('DYNAMIC_MODELS_POSTGRES_PORT', default='5432', cast=int)
    }
}
