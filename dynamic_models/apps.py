from django.apps import AppConfig


class DynamicModelsConfig(AppConfig):
    name = 'dynamic_models'
    verbose_name = 'Dynamic Models'

    def ready(self):
        """
        hook signals
        """
        import dynamic_models.receivers
