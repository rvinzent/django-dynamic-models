"""
Dummy database for generating app migrations.
"""
# pylint: disable=W0614
from .base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.dummy'
    }
}