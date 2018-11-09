INSTALLED_APPS = [
    'tests',
    'dynamic_models'
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3'
    }
}

DYNAMIC_MODELS = {
    'DYNAMIC_MODEL_CLASS': 'tests.DynamicModel',
    'DYNAMIC_FIELD_CLASS': 'tests.DynamicField',
}

SECRET_KEY = 'secret'