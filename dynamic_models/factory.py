from django.db import models
from django.apps import apps
from django.utils import timezone

from . import utils
from .exceptions import OutdatedModelError


class ModelFactory:
    def __init__(self, model_schema):
        self.schema = model_schema

    def make(self):
        self._try_unregister()
        model = type(
            self.schema.model_name,
            (models.Model,),
            self._get_attributes()
        )
        self._connect_schema_checker(model)
        return model

    def destroy(self):
        self._disconnect_schema_checker()
        self._try_unregister()

    def _get_attributes(self):
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
        return {
            field.db_column: field.make_field()
            for field in self.schema.get_fields()
        }

    def _model_meta(self):
        class Meta:
            app_label = self.schema.app_label
            db_table = self.schema.db_table
            verbose_name = self.schema.name
        return Meta

    def _connect_schema_checker(self, model):
        models.signals.pre_save.connect(
            check_model_schema,
            sender=model,
            dispatch_uid=self._get_signal_uid()
        )

    def _disconnect_schema_checker(self):
        models.signals.pre_save.disconnect(
            check_model_schema,
            dispatch_uid=self._get_signal_uid()
        )

    def _try_unregister(self):
        try:
            self.schema.unregister_model()
        except LookupError:
            pass

    def _get_signal_uid(self):
        return '{}_model_schema'.format(self.schema.model_name)
    

def check_model_schema(sender, instance, **kwargs): # pylint: disable=unused-argument
    """Check that the schema being used is the most up-to-date.

    Called on pre_save to guard against the possibility of a model schema change
    between instance instantiation and record save.
    """
    if not sender._schema.is_current_model(sender):
        raise OutdatedModelError(
            "model {} has changed".format(sender.__name__)
        )


class FieldFactory:
    # TODO: custom data types configurable in settings
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
        options = self._get_options()
        return self.constructor(**options)

    @property
    def constructor(self):
        return self.DATA_TYPES[self.schema.data_type]

    @classmethod
    def data_types(cls):
        return [(dt, dt) for dt in cls.DATA_TYPES.keys()]
        
