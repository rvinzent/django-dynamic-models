from django.db import models
from django.utils import timezone

from . import utils
from .exceptions import OutdatedModelError



class ModelFactory:

    def __init__(self, model_schema):
        self.schema = model_schema

    def make(self):
        self.schema.try_unregister_model()
        model = type(
            self.schema.model_name,
            (models.Model,),
            self.get_attributes()
        )
        _connect_schema_checker(model)
        return model

    def destroy(self):
        last_model = self.schema.try_registered_model()
        if last_model:
            _disconnect_schema_checker(last_model)
            self.schema.try_unregister_model()

    def get_attributes(self):
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
        fields = {}
        for field_schema in self.schema.get_fields():
            model_field = FieldFactory(field_schema).make()
            fields[field_schema.db_column] = model_field
        return fields

    def _model_meta(self):
        class Meta:
            app_label = self.schema.app_label
            db_table = self.schema.db_table
            verbose_name = self.schema.name
        return Meta


class FieldFactory:
    # TODO: custom data types
    DATA_TYPES = {
        'character': models.CharField,
        'text': models.TextField,
        'integer': models.IntegerField,
        'float': models.FloatField,
        'boolean': models.BooleanField,
    }

    def __init__(self, field_schema):
        self.schema = field_schema

    def make(self):
        options = self.schema.get_options()
        constructor = self.get_constructor()
        return constructor(**options)

    def get_constructor(self):
        return self.DATA_TYPES[self.schema.data_type]

    @classmethod
    def data_types(cls):
        return [(dt, dt) for dt in cls.DATA_TYPES]



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
        dispatch_uid=_get_signal_uid(model.__name__)
    )

def _disconnect_schema_checker(model):
    models.signals.pre_save.disconnect(
        check_model_schema,
        sender=model,
        dispatch_uid=_get_signal_uid(model.__name__)
    )

def _get_signal_uid(model_name):
    return '{}_model_schema'.format(model_name)
