import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = 'supersecret'

INSTALLED_APPS = [
    'tests',
    'dynamic_models',
    'django.contrib.contenttypes',
]

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

DYNAMIC_MODELS = {
    'MODEL_FIELD_SCHEMA_MODEL': 'tests.ModelFieldSchema',
}
