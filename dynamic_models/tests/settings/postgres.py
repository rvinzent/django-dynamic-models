# pylint: disable=W0614
from .base import *

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.postgresql',
		'NAME': 'dynamic_models',
		'USER': 'dynamic_models',
		'PASSWORD': 'supersecret',
		'HOST': '127.0.0.1',
		'PORT': '5432'
	}
}