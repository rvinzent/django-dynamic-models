"""
sqlite specific test settings
"""
# pylint: disable=W0614
from decouple import config
from .base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': config('DYNAMIC_MODELS_DB', default='dynamic_models.db')
    }
}