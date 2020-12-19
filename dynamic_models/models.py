from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.utils.text import slugify

from dynamic_models import config, cache
from dynamic_models.factory import ModelFactory, FieldFactory
from dynamic_models.exceptions import NullFieldChangedError, InvalidFieldNameError
from dynamic_models.schema import ModelSchemaEditor, FieldSchemaEditor
from dynamic_models.utils import ModelRegistry


class ModelSchema(models.Model):
    name = models.CharField(max_length=32, unique=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._registry = ModelRegistry(self.app_label)
        self._initial_name = self.name
        initial_model = self.get_registered_model()
        self._schema_editor = ModelSchemaEditor(initial_model)

    def save(self, **kwargs):
        super().save(**kwargs)
        cache.update_last_modified(self.model_name)
        cache.update_last_modified(self.initial_model_name)
        self._schema_editor.update_table(self._factory.make_model())
        self._initial_name = self.name

    def delete(self, **kwargs):
        self._schema_editor.drop_table(self.as_model())
        self._factory.destroy_model()
        cache.clear_last_modified(self.initial_model_name)
        super().delete(**kwargs)

    def get_registered_model(self):
        return self._registry.get_model(self.model_name)

    @property
    def _factory(self):
        return ModelFactory(self)

    @property
    def app_label(self):
        return config.dynamic_models_app_label()

    @property
    def model_name(self):
        return self.get_model_name(self.name)

    @property
    def initial_model_name(self):
        return self.get_model_name(self._initial_name)

    @classmethod
    def get_model_name(cls, name):
        return name.title().replace(" ", "")

    @property
    def db_table(self):
        parts = (self.app_label, slugify(self.name).replace("-", "_"))
        return "_".join(parts)

    def as_model(self):
        return self._factory.get_model()


class FieldSchema(models.Model):
    _PROHIBITED_NAMES = ("__module__", "_declared")
    _MAX_LENGTH_DATA_TYPES = ("character",)

    name = models.CharField(max_length=63)
    model_schema = models.ForeignKey(ModelSchema, on_delete=models.CASCADE, related_name="fields")
    null = models.BooleanField(default=False)
    class_name = models.TextField()
    kwargs = JSONField(default=dict)

    class Meta:
        unique_together = (("name", "model_schema"),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_name = self.name
        self._initial_null = self.null
        self._initial_field = self.get_registered_model_field()
        self._schema_editor = FieldSchemaEditor(self._initial_field)

    def save(self, **kwargs):
        self.validate()
        super().save(**kwargs)
        self.update_last_modified()
        model, field = self._get_model_with_field()
        self._schema_editor.update_column(model, field)

    def delete(self, **kwargs):
        model, field = self._get_model_with_field()
        self._schema_editor.drop_column(model, field)
        self.update_last_modified()
        super().delete(**kwargs)

    def validate(self):
        if self._initial_null and not self.null:
            raise NullFieldChangedError(f"Cannot change NULL field '{self.name}' to NOT NULL")

        if self.name in self.get_prohibited_names():
            raise InvalidFieldNameError(f"{self.name} is not a valid field name")

    def get_registered_model_field(self):
        latest_model = self.model_schema.get_registered_model()
        if latest_model and self.name:
            try:
                return latest_model._meta.get_field(self.name)
            except FieldDoesNotExist:
                pass

    @classmethod
    def get_prohibited_names(cls):
        # TODO: return prohbited names based on backend
        return cls._PROHIBITED_NAMES

    @classmethod
    def get_data_types(cls):
        return FieldFactory.get_data_types()

    @property
    def db_column(self):
        return slugify(self.name).replace("-", "_")

    def update_last_modified(self):
        cache.update_last_modified(self.model_schema.initial_model_name)

    def get_options(self):
        return {**self.kwargs, "null": self.null}

    def _get_model_with_field(self):
        model = self.model_schema.as_model()
        try:
            field = model._meta.get_field(self.db_column)
        except FieldDoesNotExist:
            field = None
        return model, field
