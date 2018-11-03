from django.db import models
from django.conf import settings
from model_utils import Choices, FieldTracker

from .utils import slugify_underscore


class BaseDynamicModel(models.Model):
    """
    Base model for the dynamic model definition table.
    """
    name = models.CharField(max_length=32)
    fields = models.ManyToManyField(
        'DynamicField',
        through='DynamicModelFields'
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    @property
    def model_name(self):
        """
        Default model name is the capitalized name of the instance.
        """
        return self.name.capitalize()

    @property
    def table_name(self):
        """
        Default table name is the slugified instance name with underscores
        instead of hyphens.
        """
        return slugify_underscore(self.name)

    def get_dynamic_model(self):
        pass


class BaseDynamicField(models.Model):
    """
    Base model for dynamic field definitions
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

    def __str__(self):
        return self.name

    @property
    def column_name(self):
        """
        Returns the name of the database column created by this field.
        """
        return slugify_underscore(self.name)

    def get_model_field(self, **options):
        """
        Returns a Django model field instance based on the instance's data type
        and name.
        """
        return self._field_constructor(**options)

    @classmethod
    def _field_constructor(cls, data_type):
        return cls.FIELD_TYPES[data_type]


class DynamicModel(BaseDynamicModel):
    """
    By default, a 'created_by' field is used on the dynamic field along with
    a unique together constraint between the name and user. No two models should
    have the same table name, so unique constraints must be applied to prevent
    this from happenning.
    """
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (('name', 'created_by'),)

    @property
    def table_name(self):
        return slugify_underscore(f'{super().table_name}_{self.created_by}')


class DynamicField(BaseDynamicField):
    """
    By default, a 'created_by' field is used on the dynamic field along with
    a unique together constraint between the name and user. No two fields should
    have the same name.
    """
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (('name', 'created_by'),)


class BaseDynamicModelField(models.Model):
    """
    Customizing the through table allows fields with the same name and data type
    to be declared with different options. The value of 'required' is sets
    whether a field is nullable.
    """
    model = models.ForeignKey(DynamicModel, on_delete=models.CASCADE)
    field = models.ForeignKey(DynamicField, on_delete=models.CASCADE)
    required = models.BooleanField(default=False)
    unique = models.BooleanField(default=False)

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
        if self.field.data_type == self.field.DATA_TYPES.char:
            options['max_length'] = 128
        return self.field.get_model_field(**options)


class DynamicModelField(BaseDynamicModelField):
    """
    Through model for the default implmentations of dynamic models. A non
    abstract wrapper for the base through table for use by default. To customize
    through table behavior, BaseDynamicModelField should be subclassed instead.
    """
