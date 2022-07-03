import importlib
from urllib.parse import non_hierarchical

from django.db import models
from django.utils import timezone

from dynamic_models import config
from dynamic_models.exceptions import UnsavedSchemaError
from dynamic_models.utils import ModelRegistry


class DynamicModelBase(models.base.ModelBase):
    def __instancecheck__(cls, instance):
        if issubclass(type(instance.__class__), DynamicModelBase):
            return cls._class_descriptor(instance.__class__) == cls._class_descriptor(cls)

        return super().__instancecheck__(instance)

    @staticmethod
    def _class_descriptor(class_):
        return (class_.__module__, class_.__qualname__)


class ModelFactory:
    def __init__(self, model_schema):
        self.schema = model_schema
        self.registry = ModelRegistry(model_schema.app_label)

    def get_model(self):
        if not self.schema.pk:
            raise UnsavedSchemaError(
                f"Cannot create a model for schema '{self.schema.name}'"
                " because it has not been saved to the database"
            )

        self.unregister_model()
        return DynamicModelBase(self.schema.model_name, (models.Model,), self.get_properties())

    def destroy_model(self):
        registered_model = self.get_registered_model()
        if registered_model is not None:
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
            "Meta": self._model_meta(),
        }

    def _custom_fields(self):
        return {
            field.db_column: FieldFactory(field).make_field() for field in self.schema.fields.all()
        }

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
        field_class = self.get_field_class()
        return field_class(**options)

    def get_field_class(self):
        module_name, class_name = self.schema.class_name.rsplit(".", maxsplit=1)
        module = importlib.import_module(module_name)
        return getattr(module, class_name)
