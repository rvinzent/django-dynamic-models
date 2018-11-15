from os import path

BASE_DIR = path.dirname(path.dirname(path.dirname(path.abspath(__file__))))

SECRET_KEY = 'supersecret'
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
	'dynamic_models.apps.DynamicModelsConfig',
	'django.contrib.contenttypes',
]

MIDDLEWARE = [
	'django.middleware.security.SecurityMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CACHES = {
	'default': {
		'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
	}
}

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'US/Pacific'

USE_I18N = True

USE_L10N = True

USE_TZ = True