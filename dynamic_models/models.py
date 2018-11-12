"""
Contains the base models and default implementations of dynamic model classes.
The concrete default implementations can only be used when the 'dynamic_models'
app is installed, but the base classes can be used for a custom implementation
without installing the app.
"""
from django.db import models
from django.dispatch import receiver
from django.utils.functional import cached_property
from django.utils.text import slugify
from model_utils import Choices, FieldTracker

from . import utils
from . import schema
from . import signals
from .exceptions import (
    InvalidFieldError, OutdatedModelError, NullFieldChangedError
)

# pylint: disable=no-member
# TODO: support table name changes
class AbstractModelSchema(models.Model):
    """
    Base model for the dynamic model definition table. The base model does not
    guarantee unique table names. Table name uniqueness should be handled by the
    user upon subclassing.
    """
    name = models.CharField(max_length=32, editable=False)
    _fields = models.ManyToManyField(
        'DynamicField',
        through='DynamicModelField'
    )

    class Meta:
        abstract = True

    def __init_subclass__(cls, **kwargs):
        """
        When this model is subclassed by a concrete model, the schema changing
        signal handlers will be connected.
        """
        super().__init_subclass__(**kwargs)
        if not cls._meta.abstract:
            signals.connect_table_handlers(cls)

    @cached_property
    def fields(self):
        """
        Returns the through table field instances instead of the dynamic field
        instances directly so the constraints are also included.
        """
        return self._fields.through.objects.filter(model=self)

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
    def model_hash(self):
        """
        Returns a hash unique to the dynamic model to be generated. The hash
        value will be used to keep track of the most recent model definition.
        """
        return hash(self.table_name, tuple(f for f in self.fields))

    @property
    def table_name(self):
        """
        Default table name is the slugified instance name with underscores
        instead of hyphens.
        """
        return slugify(self.name).replace('-', '_')

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
            if cached and utils.is_latest_model(cached):
                return cached

            # First try to unregister the old model to avoid Django warning
            old_model = utils.unregister_model(self.app_label, self.model_name)
            if old_model:
                utils.delete_model_hash(old_model)
                signals.disconnect_dynamic_model(old_model)

            model = type(self.model_name, (models.Model,), self._model_attrs())
            utils.set_latest_model(model)
            signals.connect_dynamic_model(model)
            return model

    def _model_meta(self):
        """
        Returns a Meta class for constructing a Django model. The Meta class
        sets the app_label, model_name, db_table, and verbose name.
        """
        class Meta: # pylint: disable=missing-docstring
            app_label = self.app_label
            model_name = self.model_name
            db_table = self.table_name
            verbose_name = self.name
        return Meta

    def _model_fields(self):
        """
        Returns the model fields of the model being generated.
        """
        return {f.name: f.get_model_field() for f in self.fields}

    def _model_attrs(self):
        """
        Returns a dict of the attributes to be used in creation of the dynamic
        model class.
        """
        attrs = {
            '__module__': '{}.models'.format(self.app_label),
            '_hash': self.model_hash
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

    name = models.CharField(max_length=32)
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


class DynamicModelField(models.Model):
    """
    The through table allows fields with the same name and data type to be
    declared with different options. The value of 'required' is sets Django's
    'null' and 'blank' options when declaring the field.
    """
    model = models.ForeignKey(
        utils.dynamic_model_class_name(),
        on_delete=models.CASCADE,
        editable=False
    )
    field = models.ForeignKey(
        utils.dynamic_field_class_name(),
        on_delete=models.CASCADE,
        editable=False
    )
    # TODO: allow changing NULL fields with method that overrides the check
    # and sets a validated default for all NULL values in the field
    required = models.BooleanField(default=False)
    unique = models.BooleanField(default=False)
    max_length = models.PositiveIntegerField(null=True)

    tracker = FieldTracker(fields=['required', 'unique', 'max_length'])

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self._check_max_length()
        self._check_null_not_changed()
        super().save(*args, **kwargs)

    def get_model_field(self):
        """
        Returns the Django model field instance represented by the instance's
        field with the applied options.
        """
        options = {
            'null': not self.required,
            'blank': not self.required,
            'unique': self.unique
        }
        # TODO: configure default max_length in settings
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
                    self.field, 'max length must be set for CharField types')
        elif self.max_length:
            raise InvalidFieldError(
                self.field, 'only CharField types should set the max length')

    def _check_null_not_changed(self):
        """
        Checks that the value of 'null' has not gone from True to False. Data
        migrations are not currently supported.
        """
        if self.tracker.previous('required') is False and self.required:
            raise NullFieldChangedError(self.field)