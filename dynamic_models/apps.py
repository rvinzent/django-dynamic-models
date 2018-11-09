from django.apps import AppConfig
from django.conf import settings

class DynamicModelsConfig(AppConfig):
    name = 'dynamic_models'

    def ready(self):
        pass