import os

from settings.base import *  # pylint: disable=wildcard-import,unused-wildcard-import


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DATABASE_NAME', 'dynamic_models_test'),
        'USER': os.environ.get('DATABASE_USER', 'postgres'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', ''),
        'HOST': 'localhost',
        'PORT':  5432,
    }
}
