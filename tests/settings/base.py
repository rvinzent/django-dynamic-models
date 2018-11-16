import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = 'supersecret'

INSTALLED_APPS = [
	'dynamic_models',
	'django.contrib.contenttypes',
]

CACHES = {
	'default': {
		'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
	}
}