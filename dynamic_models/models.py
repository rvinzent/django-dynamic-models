from django.db import models
from django.conf import settings
from model_utils import Choices

from . import fields
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

    @property
    def _model_name(self):
        """
        Default model name is the capitalized name of the instance.
        """
        return self.name.capitalize()

    @property
    def _table_name(self):
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

    name = models.CharField(max_length=32)
    data_type = models.CharField(max_length=8)

    class Meta:
        abstract = True

    @property
    def _column_name(self):
        """
        Returns the name of the database column created by this field.
        """
        return slugify_underscore(self.name)

    def get_model_field(self, **options):
        """
        Returns a Django model field instance based on the instance's data type
        and name.
        """
        return  fields.construct(self.data_type, **options)


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

    @property
    def _table_name(self):
        return slugify_underscore(f'{super()._table_name}_{self.created_by}')


    class Meta:
        unique_together = (('name', 'created_by'),)


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
    whether a field is nullable, while default provides a default value for the
    field.
    """
    class Meta:
        abstract = True

    required = models.BooleanField(default=False)
    # TODO: better default implementation, maybe create new Dynamic Field type
    # that converts types automatically depending on the data type of field
    default = models.CharField(max_length=255, null=True)


class DynamicModelField(BaseDynamicModelField):
    """
    Through model for the default implmentations of dynamic models.
    """
    # TODO: find a way to set the FK's to the user's models, so they never have
    # to touch the through field
    model = models.ForeignKey(DynamicModel, on_delete=models.CASCADE)
    field = models.ForeignKey(DynamicField, on_delete=models.CASCADE)
