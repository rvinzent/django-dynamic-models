from django.db import models
from django.apps import apps
from django.utils import timezone

from . import utils
from .exceptions import OutdatedModelError


class ModelFactory:
    def __init__(self, model_schema):
        self.schema = model_schema

    def get_model(self):
        if self._is_registered():
            model = utils.get_registered_model(self.schema)
            if self.schema.is_current_model(model):
                return model
        return self.regenerate()

    def regenerate(self):
        if self._is_registered():
            self.destroy()
        return self.build()

    def build(self):
        model = type(
            self.schema.model_name,
            (models.Model,),
            self._build_model_attributes()
        )
        self._connect_schema_checker(model)
        return model

    def destroy(self):
        self._disconnect_schema_checker()
        self._unregister_model()

    def _is_registered(self):
        model_key = self.schema.model_name.lower()
        return model_key in apps.all_models[self.schema.app_label]

    def _unregister_model(self):
        app_registry = apps.all_models[self.schema.app_label]
        del app_registry[self.schema.model_name.lower()]
        apps.clear_cache()

    def _get_signal_uid(self):
        return '{}_model_schema'.format(self.schema.model_name)

    def _build_model_attributes(self):
        return {
            **self._base_attributes(),
            **utils.default_fields(),
            **self._custom_fields()
        }

    def _base_attributes(self):
        return {
            '__module__': '{}.models'.format(self.schema.app_label),
            '_declared': timezone.now(),
            '_schema': self.schema,
            'Meta': self._model_meta(),
        }

    def _custom_fields(self):
        return {f.column_name: f.as_field() for f in self.schema.model_fields}

    def _model_meta(self):
        class Meta:
            app_label = self.schema.app_label
            db_table = self.schema.table_name
            verbose_name = self.schema.name
        return Meta

    def _connect_schema_checker(self, model):
        models.signals.pre_save.connect(
            ModelFactory.check_model_schema,
            sender=model,
            dispatch_uid=self._get_signal_uid()
        )

    def _disconnect_schema_checker(self):
        models.signals.pre_save.disconnect(
            ModelFactory.check_model_schema,
            dispatch_uid=self._get_signal_uid()
        )

    @staticmethod
    def check_model_schema(sender, instance, **kwargs): # pylint: disable=unused-argument
        """Check that the schema being used is the most up-to-date.

        Called on pre_save to guard against the possibility of a model schema change
        between instance instantiation and record save.
        """
        if not sender._schema.is_current(sender):
            raise OutdatedModelError(
                "model {} has changed".format(sender.__name__)
            )
