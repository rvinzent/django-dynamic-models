from django.db import models
from django.apps import apps
from django.utils import timezone

from . import utils
from .exceptions import OutdatedModelError, ModelDoesNotExistError


class ModelFactory:
    def __init__(self, model_schema):
        self.schema = model_schema
        self.model = None

    def get(self):
        if self.model and self.has_current_schema(self.model):
            return self.model

        model, is_current = self._get_and_check_registered_model()
        if is_current:
            self.model = model
            return self.model

        return self.regenerate()

    def regenerate(self):
        if self._is_registered():
            self.destroy()
        self.model = self.build()
        return self.model

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
        self.model = None

    def has_current_schema(self, model):
        # TODO: cache last_modified values instead
        self.schema.refresh_from_db()
        return model._declared >= self.schema.modified

    def _is_registered(self):
        return self.schema.model_name in apps.all_models[self.schema.app_label]

    def _get_and_check_registered_model(self):
        try:
            model = utils.get_registered_model(self.schema)
        except ModelDoesNotExistError:
            return None, False
        return (model, self.has_current_schema(model))

    def _unregister_model(self):
        del apps.all_models[self.schema.app_label][self.schema.model_name]
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
        # TODO: cache the last modified time instead to avoid query on each save
        sender._schema.refresh_from_db()
        if not sender._declared >= sender._schema.modified:
            raise OutdatedModelError("model {} has changed".format(sender.__name__))
