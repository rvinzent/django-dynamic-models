"""
Contains the base models and default implementations of dynamic model classes.
The concrete default implementations can only be used when the 'dynamic_models'
app is installed, but the base classes can be used for a custom implementation
without installing the app.
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
    """
    Metaclass connects the concrete model to the signal handlers responsible for
    changing model schema.
    """
    def __new__(cls, name, bases, attrs, **kwargs):
        model = super().__new__(cls, name, bases, attrs, **kwargs)
        if not model._meta.abstract:
            signals.connect_model_schema_handlers(model)
        return model


# TODO: support table name changes
class AbstractModelSchema(models.Model, metaclass=ModelSchemaBase):
    """
    Base model for the dynamic model definition table. The base model does not
    guarantee unique table names. Table name uniqueness should be handled by the
    user if necessary.
    """
    # TODO: consider unique constraint here
    name = models.CharField(max_length=32, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    @property
    def fields(self):
        """
        Returns the through table field instances instead of the dynamic field
        instances directly so the constraints are also included.
        """
        model_ct = ContentType.objects.get_for_model(self)
        return DynamicModelField.objects.prefetch_related('field').filter(
            model_content_type=model_ct,
            model_id=self.id
        )

    def add_field(self, field, **options):
        """
        Adds a field to the model schema with the options provided as extra
        keyword args. Valid options are 'required', 'unique', and 'max_length'.
        """
        return DynamicModelField.objects.create(
            model=self,
            field=field,
            **options
        )

    def update_field(self, field, **options):
        """
        Updates the given field with new options. Does not perform an UPDATE
        query so the schema changing signal is properly triggered. Raises
        DoesNotExist if the field is not found.
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
        """
        Removes the field from the model if it exists.
        """
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
        """
        Returns the app label of this model.
        """
        return self.__class__._meta.app_label

    @property
    def model_name(self):
        """
        Default model name is the capitalized name of the instance without
        spaces. Override this property to set a different naming implementation.
        """
        return self.name.title().replace(' ', '')

    @property
    def table_name(self):
        """
        Default table name is the slugified instance name with underscores
        instead of hyphens. Override this property to support a different naming
        scheme for database tables.
        """
        return '_'.join([self.app_label, slugify(self.name).replace('-', '_')])

    # TODO: support different base classes
    def get_dynamic_model(self, *, regenerate=False):
        """
        Dynamically defines the model class represented by this instance. If
        regenerate is set to True, the cache will be ignored and the model will
        be regenerated from scratch. If the model has not changed and
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
        """
        Returns a Meta class for constructing a Django model. The Meta class
        sets the app_label, model_name, db_table, and verbose name.
        """
        class Meta: # pylint: disable=missing-docstring
            app_label = self.app_label
            db_table = self.table_name
            verbose_name = self.name
        return Meta

    def _model_fields(self):
        """
        Returns the model fields of the model being generated.
        """
        return {f.field.column_name: f.get_model_field() for f in self.fields}

    def _model_attrs(self):
        """
        Returns a dict of the attributes to be used in creation of the dynamic
        model class. Base attributes include a pointer to this schema instance
        """
        attrs = {
            '__module__': '{}.models'.format(self.app_label),
            '_declared': timezone.now(),
            '_schema': self
        }
        attrs.update(
            Meta=self._model_meta(),
            **utils.default_fields(),
            **self._model_fields()
        )
        return attrs


class AbstractFieldSchema(models.Model):
    """
    Base model for dynamic field definitions. Data type choices are stored in
    the DATA_TYPES class attribute. Each data type should have a key set in
    FIELD_TYPES corresponding to the constructor to be called when generating
    the model field.
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
        """
        Returns the name of the database column created by this field.
        """
        return slugify(self.name).replace('-', '_')

    @property
    def constructor(self):
        """
        Returns a callable that constructs a Django Field instance.
        """
        return self.__class__.FIELD_TYPES[self.data_type]

    def get_model_field(self, **options):
        """
        Returns a Django model field instance based on the instance's data type
        and name.
        """
        return self.constructor(db_column=self.column_name, **options) # pylint: disable=not-callable


# TODO: Find a better way than Generic FK to support more than one concrete
# schema model or field models
class DynamicModelField(models.Model):
    """
    The through table allows fields with the same name and data type to be
    declared with different options. The value of 'required' is sets Django's
    'null' and 'blank' options when declaring the field.

    This model should only be used through the interface provided in the
    AbstractModelSchema base class.
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
        # TODO: only add fields once per model without so many unique togethers
        # Possibly better to use get_or_create / update_or_create in public API
        # but then invalid data is still allowed at the db level
        unique_together = (
            'model_content_type',
            'model_id',
            'field_content_type',
            'field_id'
        ),

    def save(self, **kwargs):
        self._check_max_length()
        self._check_null_not_changed()
        if not self.id or self.tracker.changed():
            # Save to update the model's timestamp
            self.model.save()
        super().save(**kwargs)

    def get_model_field(self):
        """
        Returns the Django model field instance represented by the instance's
        field with the applied options.
        """
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
        """
        Checks that max_length is only be set for a CharField, otherwise raises
        InvalidFieldError.
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
        """
        Checks that the value of 'required' has not gone False to True. Data
        migrations are not currently supported.
        """
        if self.tracker.previous('required') is False and self.required:
            raise NullFieldChangedError(self.field.column_name)
