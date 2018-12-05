"""Provides the base models of dynamic model schema classes.

Abstract models should be subclassed to provide extra functionality, but they
are perfectly usable without adding any additional fields.

`AbstractModelSchema` -- base model that defines dynamic models
`AbstractFieldSchema` -- base model for defining fields to use on dynamic models
`DynamicModelField`   -- through model for attaching fields to dynamic models
"""
from django.db import models
from django.dispatch import receiver
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from model_utils import Choices

from . import utils
from . import exceptions
from .schema import ModelSchemaEditor, FieldSchemaEditor, ModelSchemaCacher
from .factory import ModelFactory


class ModelSchemaBase(models.base.ModelBase):
    def __new__(cls, name, bases, attrs, **kwargs):
        model = super().__new__(cls, name, bases, attrs, **kwargs)
        if not model._meta.abstract and issubclass(model, AbstractModelSchema):
            models.signals.pre_delete.connect(drop_model_table, sender=model)
        return model

def drop_model_table(sender, instance, **kwargs):
    instance.schema_editor.delete_table()
    instance.factory.destroy()


class AbstractModelSchema(models.Model, metaclass=ModelSchemaBase):
    """Base model for the dynamic model schema table.

    Fields:
    `name`     -- used to generate the `model_name` and `table_name` properties
    `modified` -- a timestamp of the last time the instance wsa changed
    """
    name = models.CharField(max_length=32, unique=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    _cacher = ModelSchemaCacher()

    class Meta:
        abstract = True

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

    @cached_property
    def factory(self):
        return ModelFactory(self)

    @cached_property
    def schema_editor(self):
        return ModelSchemaEditor(self)

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
        super().save(**kwargs)
        self._cacher.set_last_modified(self)
        self.schema_editor.update_table()

    def as_model(self):
        """Return a dynamic model represeted by this schema instance."""
        cached = self.factory.get_model()
        return cached if self.is_current(cached) else self.factory.build()

    def is_current(self, model):
        """Checks if a model has the most up to date schema."""
        return model and model._declared >= self._cacher.get_last_modified(self)

    def add_field(self, field, **options):
        """Add a field to the model schema with the constraint options.

        Field options are passed as keyword args:
        `null`       -- sets NULL constraint on the generated field
        `unique`     -- sets UNIQUE constraint on the generated field
        `max_length` -- sets Django's max_length option on generated CharFields
        """
        field = DynamicModelField.objects.create(
            model=self,
            field=field,
            **options
        )
        self.save()
        self.schema_editor.update_field(field)
        return field

    def remove_field(self, field):
        """Remove a field from this model schema."""
        to_delete = self._get_field(field)
        self.schema_editor.delete_field(to_delete)
        to_delete.delete()
        self.save()

    def update_field(self, field, **options):
        """Updates the given model field with new options."""
        field = self._get_field(field)
        updated_field = self._set_field_options(field, options)
        self.schema_editor.update_field(field)
        self.save()
        return updated_field

    def _get_field(self, field):
        field_ct = ContentType.objects.get_for_model(field)
        return self._model_fields_queryset().get(
            field_content_type=field_ct,
            field_id=field.id
        )

    def _set_field_options(self, field, options):
        for option, value in options.items():
            setattr(field, option, value)
        return field


class AbstractFieldSchema(models.Model):
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

    def save(self, **kwargs): # pylint: disable=arguments-differ
        self._check_null_is_valid()
        super().save(**kwargs)

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
        field_kwargs = self.as_field().deconstruct[2]
        return 'max_length' in field_kwargs
