# pylint: disable=W0614
from .base import *

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.mysql',
		'NAME': 'dynamic_models',
		'USER': 'dynamic_models',
		'PASSWORD': 'supersecret',
		'HOST': '',
		'PORT': ''
	}
}