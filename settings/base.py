import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = 'supersecret'

INSTALLED_APPS = [
    'tests',
    'dynamic_models',
]

USE_TZ = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.dummy'
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}
