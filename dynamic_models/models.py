"""Provides the base models of dynamic model schema classes.

Abstract models should be subclassed to provide extra functionality, but they
are perfectly usable without adding any additional fields.

`AbstractModelSchema` -- base model that defines dynamic models
`AbstractFieldSchema` -- base model for defining fields to use on dynamic models
`DynamicModelField`   -- through model for attaching fields to dynamic models
"""
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.functional import cached_property
from django.core.exceptions import FieldDoesNotExist

from . import utils
from . import exceptions
from .schema import ModelSchemaEditor, FieldSchemaEditor
from .factory import ModelFactory, FieldFactory


LAST_MODIFIED_CACHE = utils.LastModifiedCache()


class LastModifiedBase(models.Model):
    _modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def is_current_schema(self):
        return self._modified >= self.last_modified

    @property
    def last_modified(self):
        return LAST_MODIFIED_CACHE.get(self)

    @last_modified.setter
    def last_modified(self, timestamp):
        LAST_MODIFIED_CACHE.set(self, timestamp)

    @last_modified.deleter
    def last_modified(self):
        LAST_MODIFIED_CACHE.delete(self)


class AbstractModelSchema(LastModifiedBase):
    name = models.CharField(max_length=32, unique=True)

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        """
        Initialize the schema editor with the currently registered model and the
        initial name.
        """
        super().__init__(*args, **kwargs)
        self._initial_name = self.name
        initial_model = self.try_registered_model()
        self._schema_editor = ModelSchemaEditor(initial_model)

    @property
    def schema_editor(self):
        return self._schema_editor

    @cached_property
    def registry(self):
        return utils.ModelRegistry(self.app_label)

    def save(self, **kwargs):
        super().save(**kwargs)
        self.last_modified = self._modified
        self.schema_editor.update_table(self.factory.make())

    def try_registered_model(self):
        return self.registry.try_model(self.model_name)

    def get_fields(self):
        ModelFieldSchema = utils.get_model_field_schema_model()
        return ModelFieldSchema.objects.for_model(self)

    def get_field_for_schema(self, field_schema):
        return self.get_fields().get(
            field_id=field_schema.id
        )

    def add_field(self, field_schema, **options):
        ModelFieldSchema = utils.get_model_field_schema_model()
        return ModelFieldSchema.objects.create(
            model_id=self.pk,
            field_id=field_schema.pk,
            **options
        )

    def update_field(self, field_schema, **options):
        field_to_update = self.get_field_for_schema(field_schema)
        for attr, value in options.items():
            setattr(field_to_update, attr, value)
        field_to_update.save()
        return field_to_update

    def remove_field(self, field_schema):
        self.get_field_for_schema(field_schema).delete()

    def is_current_model(self, model):
        if model._schema.pk != self.pk:
            raise ValueError("Can only be called on a model of this schema")
        return model._declared >= self.last_modified

    @property
    def factory(self):
        return ModelFactory(self)

    @property
    def app_label(self):
        return self.__class__._meta.app_label

    @property
    def model_name(self):
        return self.get_model_name(self.name)

    @property
    def initial_model_name(self):
        return self.get_model_name(self._initial_name)

    @classmethod
    def get_model_name(cls, name):
        return name.title().replace(' ', '')

    @property
    def db_table(self):
        parts = (self.app_label, slugify(self.name).replace('-', '_'))
        return '_'.join(parts)

    def as_model(self):
        return self.factory.get_model()

    def destroy_model(self):
        self.schema_editor.drop_table(self.as_model())
        self.factory.destroy()
        del self.last_modified


class AbstractFieldSchema(models.Model):
    PROHIBITED_NAMES = ('__module__', '_schema', '_declared')
    MAX_LENGTH_DATA_TYPES = ('char',)

    name = models.CharField(max_length=16)
    data_type = models.CharField(
        max_length=16,
        choices=FieldFactory.data_types(),
        editable=False
    )

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_name = self.name

    def save(self, **kwargs):
        self.validate()
        super().save(**kwargs)
        self.update_last_modified()

    def validate(self):
        if self.name in self.get_prohibited_names():
            raise exceptions.InvalidFieldNameError(
                '{} is not a valid field name'.format(self.name)
            )

    @classmethod
    def get_prohibited_names(cls):
        return cls.PROHIBITED_NAMES

    @classmethod
    def get_data_types(cls):
        return [dt[0] for dt in FieldFactory.data_types()]

    @property
    def db_column(self):
        return slugify(self.name).replace('-', '_')

    def requires_max_length(self):
        return self.data_type in self.__class__.MAX_LENGTH_DATA_TYPES

    def get_related_model_schema(self):
        ModelFieldSchema = utils.get_model_field_schema_model()
        queryset = ModelFieldSchema.objects.for_field(self)
        return (ModelFieldSchema.ModelSchema.objects.get(pk=field.model_id) for field in queryset)

    def update_last_modified(self):
        now = timezone.now()
        for model_schema in self.get_related_model_schema():
            model_schema.last_modified = now


class ModelFieldSchemaManager(models.Manager):
    def for_model(self, model_schema):
        return self.get_queryset().filter(
            model_id=model_schema.id
        )

    def for_field(self, field_schema):
        return self.get_queryset().filter(
            field_id=field_schema.id
        )


class AbstractModelFieldSchema(models.Model):
    objects = ModelFieldSchemaManager()
    ModelSchema = None
    FieldSchema = None

    model_id = models.PositiveIntegerField()
    field_id = models.PositiveIntegerField()

    null = models.BooleanField(default=False)
    unique = models.BooleanField(default=False)
    max_length = models.PositiveIntegerField(null=True, blank=True)
    primary_key = models.BooleanField(default=False)

    class Meta:
        abstract = True
        unique_together = ('model_id', 'field_id'),

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_null = self.null
        self.initial_field = self.get_latest_model_field()

    @property
    def schema_editor(self):
        return FieldSchemaEditor(self.initial_field)

    def get_latest_model_field(self):
        if not self.model_id:
            return
        model_schema = self.ModelSchema.objects.get(pk=self.model_id)
        latest_model = model_schema.try_registered_model()
        if latest_model:
            return self._extract_model_field(latest_model)

    def _extract_model_field(self, model):
        try:
            return model._meta.get_field(self.db_column)
        except FieldDoesNotExist:
            pass

    @property
    def data_type(self):
        field_schema = self.FieldSchema.objects.get(pk=self.field_id)
        return field_schema.data_type

    @property
    def db_column(self):
        field_schema = self.FieldSchema.objects.get(pk=self.field_id)
        return field_schema.db_column

    def save(self, **kwargs):
        self.validate()
        super().save(**kwargs)
        self.update_last_modified()
        self.update_column()

    def validate(self):
        if self._initial_null and not self.null:
            raise exceptions.NullFieldChangedError(
                "{} cannot be changed to NOT NULL".format(self.db_column)
            )

        if self.primary_key:
            ModelFieldSchema = utils.get_model_field_schema_model()
            model_schema = self.ModelSchema.objects.get(pk=self.model_id)
            fields = ModelFieldSchema.objects.for_model(model_schema)
            other_primary_field = fields.filter(primary_key=True).exclude(pk=self.pk)

            if other_primary_field.exists():
                other_primary_field = other_primary_field.first()
                raise exceptions.MultiplePrimaryKeyError('model already has a primary key, field_id={}'.format(other_primary_field.field_id))

    def update_last_modified(self):
        model_schema = self.ModelSchema.objects.get(pk=self.model_id)
        model_schema.last_modified = timezone.now()

    def update_column(self):
        self.schema_editor.update_column(*self._get_model_with_field())

    def drop_column(self):
        self.schema_editor.drop_column(*self._get_model_with_field())

    def _get_model_with_field(self):
        model_schema = self.ModelSchema.objects.get(pk=self.model_id)
        model = model_schema.as_model()
        return model, self._extract_model_field(model)

    def get_options(self):
        options = {'null': self.null, 'unique': self.unique, 'primary_key': self.primary_key}
        options.update(self._maybe_max_length())
        return options

    def _maybe_max_length(self):
        field_schema = self.FieldSchema.objects.get(pk=self.field_id)
        if field_schema.requires_max_length():
            self._ensure_max_length()
            return {'max_length': self.max_length}
        return {}

    def _ensure_max_length(self):
        if not self.max_length:
            self.max_length = utils.default_max_length()
            self.save()
