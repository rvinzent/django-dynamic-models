"""Provides the base models of dynamic model schema classes.

Abstract models should be subclassed to provide extra functionality, but they
are perfectly usable without adding any additional fields.

`AbstractModelSchema` -- base model that defines dynamic models
`AbstractFieldSchema` -- base model for defining fields to use on dynamic models
`DynamicModelField`   -- through model for attaching fields to dynamic models
"""
import datetime
from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from django.utils.functional import cached_property
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from model_utils import Choices

from . import utils
from . import exceptions
from .schema import ModelSchemaEditor, FieldSchemaEditor, ModelSchemaChecker
from .factory import ModelFactory


LAST_MODIFIED_CACHE = LastModifiedCache()


class ModelSchemaBase(models.base.ModelBase):
    def __new__(cls, name, bases, attrs, **kwargs):
        model = super().__new__(cls, name, bases, attrs, **kwargs)
        if not model._meta.abstract and issubclass(model, AbstractModelSchema):
            models.signals.pre_delete.connect(drop_model_table, sender=model)
        return model

def drop_model_table(sender, instance, **kwargs): # pylint: disable=unused-argument
    instance.schema_editor.drop()
    instance.schema_checker.delete()
    instance.factory.destroy()


class BaseSchema(models.Model):

    name = models.CharField(max_length=32, unique=True)
    _modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, **kwargs):
        self.validate()
        super().save(**kwargs)
        self.last_modified = self._modified

    def validate(self):
        pass

    def factory(self):
        raise NotImplementedError()

    @property
    def db_name(self):
        raise NotImplementedError()

    @cached_property
    def app_label(self):
        return self.__class__._meta.app_label

    def is_current_schema(self):
        return self._modified >= self.last_modified

    @property
    def last_modified(self):
        return LAST_MODIFIED_CACHE.get(self)

    @last_modified.setter
    def _set_last_modified(self, timestamp):
        LAST_MODIFIED_CACHE.set(self, timestamp)


class AbstractModelSchema(BaseSchema, metaclass=ModelSchemaBase):

    class Meta:
        abstract = True

    def save(self, **kwargs):
        super().save(**kwargs)
        self.schema_editor.migrate(self.factory.build())

    @property
    def factory(self):
        return ModelFactory(self)

    @property
    def schema_editor(self):
        return ModelSchemaEditor(self)

    @property
    def db_name(self):
        parts = (self.app_label, slugify(self.name).replace('-', '_'))
        return '_'.join(parts)

    def as_model(self):
        if not self.is_current_schema():
            self.refresh_from_db()
        return self.factory.get_model()

    def get_fields(self):
        return ModelFieldSchema.objects.for_model(self)


class AbstractFieldSchema(BaseSchema):

    data_type = models.CharField(
        max_length=16,
        choices=FieldFactory.data_types()
    )
    
    class Meta:
        abstract = True

    @property
    def factory(self):
        return FieldFactory(self)

    @property
    def db_name(self):
        return slugify(self.name).replace('-', '_')

    def get_models(self):
        return ModelFieldSchema.objects.for_field(self)

    def as_field(self):
        return self.factory.build()


class GenericModel:
    model_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    model_id = models.PositiveIntegerField()
    model_schema = GenericForeignKey('model_content_type', 'model_id')


class GenericField:
    field_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    field_id = models.PositiveIntegerField()
    field_schema = GenericForeignKey('field_content_type', 'field_id')


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


class ModelFieldSchema(GenericModel, GenericField, models.Model):

    objects = ModelFieldSchemaManager()

    null = models.BooleanField(default=True)
    unique = models.BooleanField(default=False)
    max_length = models.PositiveIntegerField(null=True)

    @property
    def model(self):
        return self.model_schema.as_model()

    @property
    def field(self):
        return self.model._meta.get_field(self.field_schema.db_name)

    def save(self, **kwargs):
        pass

    def validate(self):
        pass




class _AbstractModelSchema(models.Model, metaclass=ModelSchemaBase):
    """Base model for the dynamic model schema table.

    Fields:
    `name`     -- used to generate the `model_name` and `table_name` properties
    `modified` -- a timestamp of the last time the instance wsa changed
    """
    name = models.CharField(max_length=32, unique=True, editable=False)
    modified = models.DateTimeField(null=True)

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._model = None

    @cached_property
    def factory(self):
        return ModelFactory(self)

    @cached_property
    def schema_checker(self):
        return ModelSchemaChecker(self)

    @cached_property
    def schema_editor(self):
        return ModelSchemaEditor(self)

    @property
    def app_label(self):
        return self.__class__._meta.app_label

    @property
    def model_name(self):
        return self.name.title().replace(' ', '')

    @property
    def table_name(self):
        parts = [self.app_label, self.__class__.__name__, slugify(self.name)]
        return '_'.join(parts).replace('-', '_').lower()

    @property
    def model_fields(self):
        """Return the `DynamicModelField` instances related to this schema."""
        return self._model_fields_queryset().prefetch_related('field')

    def _model_fields_queryset(self):
        model_ct = ContentType.objects.get_for_model(self)
        return DynamicModelField.objects.filter(
            model_content_type=model_ct,
            model_id=self.id
        )

    def save(self, **kwargs):
        self.modified = timezone.now()
        super().save(**kwargs)
        self.schema_checker.update(self.modified)
        self.schema_editor.update()

    def as_model(self):
        """Return a dynamic model represeted by this schema instance."""
        if not (self._model and self.schema_checker.is_current_model(self._model)):
            self._model = self.factory.regenerate()
        return self._model

    def is_current_model(self, model):
        return self.schema_checker.is_current_model(model)

    def add_field(self, field, **options):
        """Add a field to the model schema with the constraint options.

        Field options are passed as keyword args:
        `null`       -- sets NULL constraint on the generated field
        `unique`     -- sets UNIQUE constraint on the generated field
        `max_length` -- sets Django's max_length option on generated CharFields
        """
        return DynamicModelField.objects.create(
            model=self,
            field=field,
            **options
        )

    def remove_field(self, field_schema):
        """Remove a field from this model schema."""
        to_delete = self.get_field(field_schema)
        to_delete.delete()

    def update_field(self, field_schema, **options):
        """Updates the given model field with new options."""
        field = self.get_field(field_schema)
        updated_field = self._set_field_options(field, options)
        updated_field.save()
        return updated_field

    def get_field(self, field_schema):
        field_ct = ContentType.objects.get_for_model(field_schema)
        return self._model_fields_queryset().get(
            field_content_type=field_ct,
            field_id=field_schema.id
        )

    def _set_field_options(self, field, options):
        for option, value in options.items():
            setattr(field, option, value)
        return field


class _AbstractFieldSchema(models.Model):
    """Base model for dynamic field definitions.

    Data type choices are stored in the DATA_TYPES class attribute. DATA_TYPES
    should be a valid `choices` object. Each data type should have a key set in
    FIELD_TYPES mapping to the constructor of a Django `Field` class.
    """
    # TODO: support foreign keys
    DATA_TYPES = Choices(
        ('char', 'short text'),
        ('text', 'long text'),
        ('int', 'integer'),
        ('float', 'float'),
        ('bool', 'boolean'),
        ('date', 'date')
    )

    FIELD_TYPES = {
        DATA_TYPES.char: models.CharField,
        DATA_TYPES.text: models.TextField,
        DATA_TYPES.int: models.IntegerField,
        DATA_TYPES.float: models.FloatField,
        DATA_TYPES.date: models.DateTimeField,
        DATA_TYPES.bool: models.BooleanField
    }

    assert set(dt[0] for dt in DATA_TYPES).issubset(FIELD_TYPES.keys()),\
        "All DATA_TYPES must be present in the FIELD_TYPES map"

    name = models.CharField(max_length=32, unique=True, editable=False)
    data_type = models.CharField(
        max_length=8,
        choices=DATA_TYPES,
        editable=False
    )
    class Meta:
        abstract = True

    @property
    def column_name(self):
        """Return the name of the database column created by this field."""
        return slugify(self.name).replace('-', '_')

    @property
    def constructor(self):
        """Return a callable that constructs a Django Field instance."""
        return self.__class__.FIELD_TYPES[self.data_type]

    def as_field(self, **options):
        """Returns an unassociated Django Field instance."""
        return self.constructor(db_column=self.column_name, **options) # pylint: disable=not-callable

    def get_from_model(self, model):
        return model._meta.get_field(self.column_name)


# Export default data types from the class
DefaultDataTypes = AbstractFieldSchema.DATA_TYPES # pylint: disable=invalid-name


class DynamicModelField(models.Model):
    """Through table for model schema objects to field schema objects.

    This model should only be interacted with by the interface provided in the
    AbstractModelSchema base class to allow for proper schema changes.
    """
    model_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='model_content_types',
        editable=False
    )
    model_id = models.PositiveIntegerField(editable=False)
    model = GenericForeignKey('model_content_type', 'model_id')

    field_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='field_content_types',
        editable=False
    )
    field_id = models.PositiveIntegerField(editable=False)
    field = GenericForeignKey('field_content_type', 'field_id')

    # TODO: add index and default value options
    # TODO: allow changing NULL fields
    null = models.BooleanField(default=True)
    unique = models.BooleanField(default=False)
    max_length = models.PositiveIntegerField(null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_null = self.null

    class Meta:
        unique_together = (
            'model_content_type',
            'model_id',
            'field_content_type',
            'field_id'
        ),

    @property
    def column_name(self):
        return self.field.column_name

    @cached_property
    def schema_editor(self):
        return FieldSchemaEditor(self.model, self.field)

    @cached_property
    def schema_checker(self):
        return self.model.schema_checker

    def save(self, **kwargs): # pylint: disable=arguments-differ
        self._check_null_is_valid()
        super().save(**kwargs)
        self.update_schema()

    def update_schema(self):
        self.schema_checker.update(timezone.now())
        self.schema_editor.update()

    def _check_null_is_valid(self):
        if self._initial_null and not self.null:
            raise exceptions.NullFieldChangedError(
                "{} cannot be changed to NOT NULL".format(self.column_name)
            )

    def as_field(self):
        """Return the Django model field instance with configured constraints."""
        options = {'null': self.null, 'unique': self.unique}
        self._add_max_length_option(options)
        return self.field.as_field(**options)

    def _add_max_length_option(self, options):
        if self._requires_max_length():
            self._ensure_max_length()
            options['max_length'] = self.max_length
        return options

    def _ensure_max_length(self):
        if not self.max_length:
            self.max_length = utils.default_max_length()

    def _requires_max_length(self):
        return issubclass(self.field.constructor, models.CharField)


@receiver(models.signals.pre_delete, sender=DynamicModelField)
def drop_table_field(sender, instance, **kwargs):
    instance.schema_editor.drop()
    instance.schema_checker.update()
