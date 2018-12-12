from django.db import models
from django.utils import timezone

from . import utils
from .exceptions import OutdatedModelError


class FieldFactory:
    # TODO: custom data types
    DATA_TYPES = {
        'character': models.CharField,
        'text': models.TextField,
        'integer': models.IntegerField,
        'float': models.FloatField,
        'boolean': models.BooleanField,
    }

    def make(self, schema):
        options = schema.get_options()
        constructor = self.get_constructor(schema)
        return constructor(**options)

    def get_constructor(self, schema):
        return self.DATA_TYPES[schema.data_type]

    @classmethod
    def data_types(cls):
        return [(dt, dt) for dt in cls.DATA_TYPES]


class ModelFactory:

    field_factory = FieldFactory()

    def make(self, schema):
        schema.try_unregister_model()
        model = type(
            schema.model_name,
            (models.Model,),
            self.get_attributes(schema)
        )
        _connect_schema_checker(model)
        return model

    def destroy(self, schema):
        _disconnect_schema_checker(schema)
        schema.try_unregister_model()

    def get_attributes(self, schema):
        return {
            **self._base_attributes(schema),
            **utils.default_fields(),
            **self._custom_fields(schema)
        }

    def _base_attributes(self, schema):
        return {
            '__module__': '{}.models'.format(schema.app_label),
            '_declared': timezone.now(),
            '_schema': schema,
            'Meta': self._model_meta(schema),
        }

    def _custom_fields(self, schema):
        fields = {}
        for field in schema.get_fields():
            model_field = self.field_factory.make(field)
            fields[field.db_column] = model_field
        return fields

    def _model_meta(self, schema):
        class Meta:
            app_label = schema.app_label
            db_table = schema.db_table
            verbose_name = schema.name
        return Meta


def check_model_schema(sender, instance, **kwargs): # pylint: disable=unused-argument
    """Check that the schema being used is the most up-to-date.

    Called on pre_save to guard against the possibility of a model schema change
    between instance instantiation and record save.
    """
    if not sender._schema.is_current_model(sender):
        raise OutdatedModelError(
            "model {} has changed".format(sender.__name__)
        )

def _connect_schema_checker(model):
    models.signals.pre_save.connect(
        check_model_schema,
        sender=model,
        dispatch_uid=_get_signal_uid(model._schema)
    )

def _disconnect_schema_checker(schema):
    models.signals.pre_save.disconnect(
        check_model_schema,
        dispatch_uid=_get_signal_uid(schema)
    )

def _get_signal_uid(schema):
    return '{}_model_schema'.format(schema.model_name)
