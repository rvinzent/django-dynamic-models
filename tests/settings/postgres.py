from settings.base import *  # pylint: disable=wildcard-import,unused-wildcard-import


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'dynamic_models_test',
        'USER': 'postgres',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'PORT':  5432,
    }
}
