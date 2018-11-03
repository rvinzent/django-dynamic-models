"""
Contains the base models and default implementations of dynamic model classes.
The concrete default implementations can only be used when the 'dynamic_models'
app is installed, but the base classes can be used for a custom implementation
without installing the app.
"""
from django.db import models
from model_utils import Choices

from . import utils


class BaseDynamicModel(models.Model):
    """
    Base model for the dynamic model definition table. The base model does not
    guarantee unique table names. Table name uniqueness should be handled by the
    user upon subclassing.
    """
    name = models.CharField(max_length=32)
    _fields = models.ManyToManyField(
        'DynamicField',
        through='DynamicModelField'
    )

    class Meta:
        abstract = True

    @property
    def fields(self):
        """
        Returns the through table field instances instead of the dynamic field
        instances directly .
        """
        return self._fields.through.objects.filter(model=self)

    @property
    def model_name(self):
        """
        Default model name is the capitalized name of the instance without
        spaces.
        """
        return self.name.title().replace(' ', '')

    @property
    def table_name(self):
        """
        Default table name is the slugified instance name with underscores
        instead of hyphens.
        """
        return utils.slugify_underscore(self.name)

    def get_dynamic_model(self):
        """
        Dynamically defines the model class represented by this instance. If
        regenerate is set to True, the cache will be ignored and the model will
        be regenerated from scratch. If the model has not changed and
        regenerate is set to False, the model will be retrieved from the cache.
        """
        return type(self.model_name, (models.Model,), self._model_attrs())

    def _model_meta(self):
        """
        Returns a Meta class for constructing a Django model. The Meta class
        sets the app_label, model_name, db_table, and verbose name.
        """
        class Meta:                          # pylint: disable=missing-docstring
            app_label = self._meta.app_label
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
        attrs = {'__module__': "{}.models".format(self._meta.app_label)}
        attrs.update(
            Meta=self._model_meta(),
            **utils.default_fields(),
            **self._model_fields()
        )
        return attrs


class BaseDynamicField(models.Model):
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
        return utils.slugify_underscore(self.name)

    def get_model_field(self, **options):
        """
        Returns a Django model field instance based on the instance's data type
        and name.
        """
        constructor = self._field_constructor(self.data_type)
        return constructor(db_column=self.column_name, **options)

    @classmethod
    def _field_constructor(cls, data_type):
        return cls.FIELD_TYPES[data_type]


class BaseDynamicModelField(models.Model):
    """
    Customizing the through table allows fields with the same name and data type
    to be declared with different options. The value of 'required' is sets
    Django's 'null' and 'blank' options when declaring the field.
    """
    model = models.ForeignKey(
        utils.dynamic_model_class_name(),
        on_delete=models.CASCADE
    )
    field = models.ForeignKey(
        utils.dynamic_field_class_name(),
        on_delete=models.CASCADE
    )
    required = models.BooleanField(default=False)
    unique = models.BooleanField(default=False)
    max_length = models.PositiveIntegerField(null=True)
    # TODO: indexable fields

    class Meta:
        abstract = True

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
        if self.max_length:
            options['max_length'] = self.max_length
        return self.field.get_model_field(**options) # pylint: disable=no-member


class DynamicModelField(BaseDynamicModelField):
    """
    Through model for the default implmentations of dynamic models. A non
    abstract wrapper for the base through table for use by default. To customize
    through table behavior, BaseDynamicModelField should be subclassed instead.
    """
