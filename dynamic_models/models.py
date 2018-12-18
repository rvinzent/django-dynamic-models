"""Provides the base models of dynamic model schema classes.

Abstract models should be subclassed to provide extra functionality, but they
are perfectly usable without adding any additional fields.

`AbstractModelSchema` -- base model that defines dynamic models
`AbstractFieldSchema` -- base model for defining fields to use on dynamic models
`DynamicModelField`   -- through model for attaching fields to dynamic models
"""
from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from django.utils.functional import cached_property
from django.core.exceptions import FieldDoesNotExist
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

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


class ModelSchemaBase(models.base.ModelBase):
    def __new__(cls, name, bases, attrs, **kwargs):
        model = super().__new__(cls, name, bases, attrs, **kwargs)
        if not model._meta.abstract and issubclass(model, AbstractModelSchema):
            models.signals.pre_delete.connect(drop_model_table, sender=model)
        return model


def drop_model_table(sender, instance, **kwargs): # pylint: disable=unused-argument
    instance.destroy_model()


class AbstractModelSchema(LastModifiedBase, metaclass=ModelSchemaBase):
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
        return ModelFieldSchema.objects.for_model(self)

    def get_field_for_schema(self, field_schema):
        field_ct = ContentType.objects.get_for_model(field_schema)
        return self.get_fields().get(
            field_content_type=field_ct,
            field_id=field_schema.id
        )

    def add_field(self, field_schema, **options):
        return ModelFieldSchema.objects.create(
            model_schema=self,
            field_schema=field_schema,
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
    MAX_LENGTH_DATA_TYPES = ('character',)

    name = models.CharField(max_length=16)
    data_type = models.CharField(
        max_length=16,
        choices=FieldFactory.data_types()
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

    @property
    def db_column(self):
        return slugify(self.name).replace('-', '_')

    def requires_max_length(self):
        return self.data_type in self.__class__.MAX_LENGTH_DATA_TYPES

    def get_related_models(self):
        queryset = ModelFieldSchema.objects.for_field(self).prefetch_related('model_schema')
        return (field.model_schema for field in queryset)

    def update_last_modified(self):
        now = timezone.now()
        for model_schema in self.get_related_models():
            model_schema.last_modified = now


class ModelFieldSchemaManager(models.Manager):
    def for_model(self, model_schema):
        return self.get_queryset().filter(
            model_content_type=ContentType.objects.get_for_model(model_schema),
            model_id=model_schema.id
        )

    def for_field(self, field_schema):
        return self.get_queryset().filter(
            field_content_type=ContentType.objects.get_for_model(field_schema),
            field_id=field_schema.id
        )


class GenericModel(models.Model):
    model_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='model_field_columns'
    )
    model_id = models.PositiveIntegerField()
    model_schema = GenericForeignKey('model_content_type', 'model_id')

    class Meta:
        abstract = True


class GenericField(models.Model):
    field_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    field_id = models.PositiveIntegerField()
    field_schema = GenericForeignKey('field_content_type', 'field_id')

    class Meta:
        abstract = True


class ModelFieldSchema(GenericModel, GenericField):

    objects = ModelFieldSchemaManager()

    null = models.BooleanField(default=False)
    unique = models.BooleanField(default=False)
    max_length = models.PositiveIntegerField(null=True)

    class Meta:
        unique_together = (
            'model_content_type', 'model_id', 'field_content_type', 'field_id'
        ),

    def  __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_null = self.null
        self.initial_field = self.get_latest_model_field()

    @property
    def schema_editor(self):
        return FieldSchemaEditor(self.initial_field)

    def get_latest_model_field(self):
        latest_model = self.model_schema.try_registered_model()
        if latest_model:
            return self._extract_model_field(latest_model)

    def _extract_model_field(self, model):
        try:
            return model._meta.get_field(self.db_column)
        except FieldDoesNotExist:
            pass

    @property
    def data_type(self):
        return self.field_schema.data_type

    @property
    def db_column(self):
        return self.field_schema.db_column

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

    def update_last_modified(self):
        self.model_schema.last_modified = timezone.now()

    def update_column(self):
        self.schema_editor.update_column(*self._get_model_with_field())

    def drop_column(self):
        self.schema_editor.drop_column(*self._get_model_with_field())

    def _get_model_with_field(self):
        model = self.model_schema.as_model()
        return model, self._extract_model_field(model)

    def get_options(self):
        options = {'null': self.null, 'unique': self.unique}
        options.update(self._maybe_max_length())
        return options

    def _maybe_max_length(self):
        if self.field_schema.requires_max_length():
            self._ensure_max_length()
            return {'max_length': self.max_length}
        return {}

    def _ensure_max_length(self):
        if not self.max_length:
            self.max_length = utils.default_max_length()
            self.save()


@receiver(models.signals.pre_delete, sender=ModelFieldSchema)
def drop_table_column(sender, instance, **kwargs): # pylint: disable=unused-argument
    instance.drop_column()
    instance.update_last_modified()
