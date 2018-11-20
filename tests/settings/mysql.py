"""
MySQL specific test settings.
"""
# pylint: disable=W0614
from decouple import config
from .base import *

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.mysql',
		'NAME': config('DYNAMIC_MODELS_DB', default='dynamic_models'),
		'USER': config('DYNAMIC_MODELS_DB_USER', default='dynamic_models'),
		'PASSWORD': config('DYNAMIC_MODELS_DB_PASSWORD', default=''),
		'HOST': config('DYNAMIC_MODELS_MYSQL_HOST', default='127.0.0.1'),
		'PORT': config('DYNAMIC_MODELS_MYSQL_PORT', default=3306, cast=int)
	}
}