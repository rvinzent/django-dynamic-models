import importlib

from django.db import models
from django.utils import timezone

from dynamic_models import config
from dynamic_models.exceptions import OutdatedModelError, UnsavedSchemaError
from dynamic_models.utils import ModelRegistry, is_current_model


class ModelFactory:
    def __init__(self, model_schema):
        self.schema = model_schema
        self.registry = ModelRegistry(model_schema.app_label)

    def get_model(self):
        registered = self.get_registered_model()
        if registered and is_current_model(registered):
            return registered
        return self.make_model()

    def make_model(self):
        if not self.schema.pk:
            raise UnsavedSchemaError(
                f"Cannot create a model for schema '{self.schema.name}'"
                " because it has not been saved to the database"
            )
        self.unregister_model()
        model = type(self.schema.model_name, (models.Model,), self.get_properties())
        _connect_schema_checker(model)
        return model

    def destroy_model(self):
        last_model = self.get_registered_model()
        if last_model:
            _disconnect_schema_checker(last_model)
            self.unregister_model()

    def get_registered_model(self):
        return self.registry.get_model(self.schema.initial_model_name)

    def unregister_model(self):
        try:
            self.registry.unregister_model(self.schema.initial_model_name)
        except LookupError:
            pass

    def get_properties(self):
        return {
            **self._base_properties(),
            **config.default_fields(),
            **self._custom_fields(),
        }

    def _base_properties(self):
        return {
            "__module__": "{}.models".format(self.schema.app_label),
            "_declared": timezone.now(),
            "Meta": self._model_meta(),
        }

    def _custom_fields(self):
        fields = {}
        for field_schema in self.schema.fields.all():
            model_field = FieldFactory(field_schema).make_field()
            fields[field_schema.db_column] = model_field
        return fields

    def _model_meta(self):
        class Meta:
            app_label = self.schema.app_label
            db_table = self.schema.db_table
            verbose_name = self.schema.name

        return Meta


class FieldFactory:
    def __init__(self, field_schema):
        self.schema = field_schema

    def make_field(self):
        options = self.schema.get_options()
        constructor = self.get_constructor()
        return constructor(**options)

    def get_constructor(self):
        module_name, class_name = self.schema.class_name.rsplit(".", maxsplit=1)
        module = importlib.import_module(module_name)
        return getattr(module, class_name)


def check_model_schema(sender, instance, **kwargs):
    """
    Check that the schema being used is the most up-to-date.

    Called on pre_save to guard against the possibility of a model schema change
    between instance instantiation and record save.
    """
    if not is_current_model(sender):
        raise OutdatedModelError(f"model {sender.__name__} has changed")


def _connect_schema_checker(model):
    models.signals.pre_save.connect(
        check_model_schema, sender=model, dispatch_uid=_get_signal_uid(model.__name__)
    )


def _disconnect_schema_checker(model):
    models.signals.pre_save.disconnect(
        check_model_schema, sender=model, dispatch_uid=_get_signal_uid(model.__name__)
    )


def _get_signal_uid(model_name):
    return "{}_model_schema".format(model_name)
