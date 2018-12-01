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
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from model_utils import Choices, FieldTracker

from . import utils
from . import signals
from .exceptions import InvalidFieldError, NullFieldChangedError


# TODO: Move this to __init_subclass__ 
class ModelSchemaBase(models.base.ModelBase):
    """Metaclass connects the concrete model to the signal handlers.
    
    The handlers are responsible for changing model schema.
    """
    def __new__(cls, name, bases, attrs, **kwargs):
        model = super().__new__(cls, name, bases, attrs, **kwargs)
        if not model._meta.abstract:
            signals.connect_model_schema_handlers(model)
        return model


# TODO: support table name changes
class AbstractModelSchema(models.Model, metaclass=ModelSchemaBase):
    """Base model for the dynamic model schema table.
    
    The base model does not guarantee unique table names. Table name uniqueness
    should be handled by the user with appropriate `unique` or `unique_together`
    constraints.
    
    Fields:
    `name`     -- used to generate the `model_name` and `table_name` properties
    `modified` -- a timestamp of the last time the instance wsa changed
    """
    # TODO: consider unique constraint here
    name = models.CharField(max_length=32, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    @property
    def fields(self):
        """Return the `DynamicModelField` instances related to this schema.
        
        Field instances are not returned directly so the constraints are also
        included in the returned objects. The instances returned are those
        responsible for the
        """
        model_ct = ContentType.objects.get_for_model(self)
        return DynamicModelField.objects.prefetch_related('field').filter(
            model_content_type=model_ct,
            model_id=self.id
        )

    def add_field(self, field, **options):
        """Add a field to the model schema with the constraint options.

        Field options are passed as keyword args:
        `required`   -- sets NULL constraint on the generated field
        `unique`     -- sets UNIQUE constraint on the generated field
        `max_length` -- sets Django's max_length option on generated CharFields
        """
        return DynamicModelField.objects.create(
            model=self,
            field=field,
            **options
        )

    def update_field(self, field, **options):
        """Updates the given model field with new options.
        
        Does not perform an UPDATE query so the schema changing signal is
        properly triggered. Raise DoesNotExist if the field is not found.
        """
        field_ct = ContentType.objects.get_for_model(field)
        field = DynamicModelField.objects.get(
            field_content_type=field_ct,
            field_id=field.id
        )
        for option, value in options.items():
            setattr(field, option, value)
        field.save()
        return field

    def remove_field(self, field):
        """Removes the field from the model if it exists."""
        content_types = ContentType.objects.get_for_models(self, field)
        field = DynamicModelField.objects.filter(
            model_content_type=content_types[self],
            model_id=self.id,
            field_content_type=content_types[field],
            field_id=field.id,
        )
        field.delete()

    @property
    def app_label(self):
        """Returns the app label of this model."""
        return self.__class__._meta.app_label

    @property
    def model_name(self):
        """Return a string name of the dynamic model class.

        Default model name is the capitalized `name` field of the instance
        without spaces. Override this property to set a different naming
        implementation on generated dynamic models.
        """
        return self.name.title().replace(' ', '')

    @property
    def table_name(self):
        """Return a string name of the database table to be generated.

        Default table name is the slugified `name` of the instance with
        underscores instead of hyphens. Override this property to support a
        different naming scheme for database tables. The generated name should
        be unique per database.
        """
        return '_'.join([self.app_label, slugify(self.name)]).replace('-', '_')

    # TODO: support different base classes
    def get_dynamic_model(self, *, regenerate=False):
        """Return a dynamic model constructed with the built-in `type` function.

        Keyword arguments:
        `regenerate` -- ignore cache and force the class to be redefined

        If regenerate is set to True, the cache will be ignored and the model
        will be regenerated from scratch. If the model has not changed and
        regenerate is set to False, the model will be retrieved from the cache.
        """
        if not regenerate:
            cached = utils.get_cached_model(self.app_label, self.model_name)
            if cached and utils.has_current_schema(self, cached):
                return cached

        # First try to unregister the old model to avoid Django warning
        utils.unregister_model(self.app_label, self.model_name)
        model = type(self.model_name, (models.Model,), self._model_attrs())
        signals.connect_dynamic_model(model)
        return model

    def _model_meta(self):
        """Returns a Meta object for constructing a Django model.
        
        The Meta class determines the model's app_label, model_name,
        db_table, and verbose_name attributes.
        """
        class Meta: # pylint: disable=missing-docstring
            app_label = self.app_label
            db_table = self.table_name
            verbose_name = self.name
        return Meta

    def _model_attrs(self):
        """Return a dict of the attributes of the dynamic model.
        
        Base attributes:
        `__module__` -- required attribute of all Django models
        `_declared`  -- timestamp of the moment of the model's definition
        `_schema`    -- a reference to this instance

        Dynamic attributes:
        - fields declared settings.DYNAMIC_MODELS['DEFAULT_FIELDS`]
        - fields generated from the `_model_fields` method
        """
        return {
            '__module__': '{}.models'.format(self.app_label),
            '_declared': timezone.now(),
            '_schema': self,
            'Meta': self._model_meta(),
            **utils.default_fields(),
            **{f.field.column_name: f.get_model_field() for f in self.fields}
        }


class AbstractFieldSchema(models.Model):
    """Base model for dynamic field definitions.
    
    Data type choices are stored in the DATA_TYPES class attribute. DATA_TYPES
    should be a valid `choices` object.
    
    Each data type should have a key set in FIELD_TYPES mapping to the
    constructor of a Django `Field` class.

    Fields:
    `name`      -- the name of the field on the dynamic model
    `data_type` -- the data type of the field on the dynamic model
    """
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

    name = models.CharField(max_length=32, editable=False)
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

    def get_model_field(self, **options):
        """Returns a Django model field instance to add to a dynamic model."""
        return self.constructor(db_column=self.column_name, **options) # pylint: disable=not-callable


# TODO: Find a better way than Generic FK to support more than one concrete
# schema model or field models
class DynamicModelField(models.Model):
    """Through table for model schema objects to field schema objects.

    This model should only be interacted with by the interface provided in the
    AbstractModelSchema base class. It is responsible for generating model
    fields with customized constraints.

    Fields:
    `model`      -- a generic foreign key pointing to an AbstractModelSchema 
    `field`      -- a generic foreign key pointing to an AbstractFieldSchema
    `required`   -- sets the NULL contstraint; default: False
    `unique`     -- sets the UNIQUE constraint; default: False
    `max_length` -- sets the `max_length` option required for `CharField`s
    `tracker`    -- a `FieldTracker` instance from `django-model-utils` package
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

    # TODO: add index option
    # TODO: allow changing NULL fields with method that overrides the check
    # and sets a validated default for all NULL values in the field
    required = models.BooleanField(default=False)
    unique = models.BooleanField(default=False)
    max_length = models.PositiveIntegerField(null=True)

    tracker = FieldTracker(fields=['required', 'unique', 'max_length'])

    class Meta:
        unique_together = (
            'model_content_type',
            'model_id',
            'field_content_type',
            'field_id'
        ),

    def save(self, **kwargs):
        """Run field validation and update model's timestamp then save to db."""
        self._check_max_length()
        self._check_null_not_changed()
        if not self.id or self.tracker.changed():
            self.model.save() # Save to update the model's timestamp
        super().save(**kwargs)

    def get_model_field(self):
        """Return the Django model field instance with constraint options."""
        # TODO: configure default max_length in settings
        # TODO: default field value option
        options = {
            'null': not self.required,
            'blank': not self.required,
            'unique': self.unique
        }
        if self.max_length:
            options['max_length'] = self.max_length
        return self.field.get_model_field(**options)

    def _check_max_length(self):
        """Check that `max_length` is only set for `CharField` generation.
        
        Raise `InvalidFieldError` if incorrectly configured.
        """
        if self.field.constructor == models.CharField:
            if not self.max_length:
                raise InvalidFieldError(
                    self.field.column_name,
                    'max length must be set for CharField types')
        elif self.max_length:
            raise InvalidFieldError(
                self.field.column_name,
                'only CharField types should set the max length')

    def _check_null_not_changed(self):
        """Check the value of `required` has not been turned from False to True.
        
        Data migrations are not currently supported, but are planned in a future
        release in which case this method will no longer be necessary.
        """
        if self.tracker.previous('required') is False and self.required:
            raise NullFieldChangedError(self.field.column_name)
