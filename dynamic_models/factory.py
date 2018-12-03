from django.db import models
from django.utils import timezone

from . import utils
from .exceptions import OutdatedModelError


class ModelFactory:
    def __init__(self, model_schema):
        self.schema = model_schema

    def build(self):
        model = type(
            self.schema.model_name,
            (models.Model,),
            self._build_model_attributes()
        )
        self._connect_schema_checker(model)
        return model

    def _connect_schema_checker(self, model):
        models.signals.pre_save.connect(
            check_model_schema,
            sender=model,
            dispatch_uid=self._get_signal_uid()
        )

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
            '_schema': self,
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

    def _get_signal_uid(self):
        return '{}_model_schema'.format(self.schema.model_name)


def check_model_schema(sender, instance, **kwargs):
    """Check that the schema being used is the most up-to-date.

    Called on pre_save to guard against the possibility of a model schema change
    between instance instantiation and record save.
    """
    # TODO: cache the last modified time instead to avoid query on each save
    sender._schema.refresh_from_db()
    if not sender._schema._has_current_schema(sender):
        raise OutdatedModelError("model {} has changed".format(sender.__name__))
