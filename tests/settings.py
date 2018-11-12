INSTALLED_APPS = [
    'dynamic_models',
    'tests',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3'
    }
}

DYNAMIC_MODELS = {
    'DYNAMIC_MODEL_CLASS': 'tests.SimpleModelSchema',
    'DYNAMIC_FIELD_CLASS': 'tests.SimpleFieldSchema',
}

SECRET_KEY = 'secret'