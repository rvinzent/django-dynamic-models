"""Provides the base models of dynamic model schema classes.

Abstract models should be subclassed to provide extra functionality, but they
are perfectly usable without adding any additional fields.

`AbstractModelSchema` -- base model that defines dynamic models
`AbstractFieldSchema` -- base model for defining fields to use on dynamic models
`DynamicModelField`   -- through model for attaching fields to dynamic models
"""
from functools import partial

from django.db import models
from django.apps import apps
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from model_utils import Choices

from . import utils
from . import signals
from . import schema
from . import exceptions


# TODO: Move this to __init_subclass__
class ModelSchemaBase(models.base.ModelBase):
    def __new__(cls, name, bases, attrs, **kwargs):
        model = super().__new__(cls, name, bases, attrs, **kwargs)
        if not model._meta.abstract:
            signals.connect_model_schema_handlers(model)
        return model


class AbstractModelSchema(models.Model, metaclass=ModelSchemaBase):
    """Base model for the dynamic model schema table.

    Fields:
    `name`     -- used to generate the `model_name` and `table_name` properties
    `modified` -- a timestamp of the last time the instance wsa changed
    """
    name = models.CharField(max_length=32, unique=True, editable=False)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._old_table_name = self.table_name

    @property
    def app_label(self):
        return self.__class__._meta.app_label

    @property
    def model_name(self):
        return self.name.title().replace(' ', '')

    @property
    def table_name(self):
        parts = [self.app_label, self.__class__.__name__, slugify(self.name)]
        return '_'.join(parts).replace('-', '_')

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

    @property
    def schema_editor(self):
        return schema.ModelSchemaEditor(self)

    @property
    def old_table_name(self):
        return self._old_table_name

    def save(self, **kwargs):
        change_type = self._get_change_type()
        super().save(**kwargs)
        self._apply_schema_change(change_type)

    def _get_change_type(self):
        if self.id is None:
            return 'create'
        elif self._name_changed():
            return 'modify'

    def _name_changed(self):
        return self.old_table_name != self.table_name

    def _apply_schema_change(self, change_type):
        with self.schema_editor as editor:
            self._execute_schema_change(change_type, editor)

    def _execute_schema_change(self, change_type, editor):
        # TODO: Change type enum
        if change_type == 'create':
            editor.create_table()
        elif change_type == 'modify':
            editor.alter_table()

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

    def remove_field(self, field):
        """Remove a field from this model schema."""
        self._get_field(field).delete()

    def update_field(self, field, **options):
        """Updates the given model field with new options."""
        old_field = self._get_field(field)
        updated_field = self._set_field_options(old_field, options)
        updated_field.save()
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

    def as_model(self):
        """Return a dynamic model represeted by this schema instance."""
        try:
            return self._try_cached_model()
        except exceptions.ModelDoesNotExistError:
            pass
        model = self._build_model()
        signals.connect_dynamic_model(model)
        return model

    def _build_model(self):
        return type(self.model_name, (models.Model,), self._model_attributes())

    def _try_cached_model(self):
        try:
            return self._cached_model()
        except exceptions.OutdatedModelError:
            self._unregister_model()

    def _cached_model(self):
        model = utils.get_model(self.app_label, self.model_name)
        self._check_model_is_current(model)
        return model

    def _unregister_model(self):
        try:
            del apps.all_models[self.app_label][self.model_name]
        except KeyError as err:
            raise exceptions.ModelDoesNotExistError() from err
        else:
            signals.disconnect_dynamic_model(self.model_name)

    def _check_model_is_current(self, model):
        if not self._has_current_schema(model):
            raise exceptions.OutdatedModelError()

    def _has_current_schema(self, model):
        return model._declared >= self.modified # pylint: disable=protected-access

    def _model_attributes(self):
        return {
            **self._base_fields(),
            **utils.default_fields(),
            **self._custom_fields()
        }

    def _base_fields(self):
        return {
            '__module__': '{}.models'.format(self.app_label),
            '_declared': timezone.now(),
            '_schema': self,
            'Meta': self._model_meta(),
        }

    def _custom_fields(self):
        return {f.column_name: f.as_field() for f in self.model_fields}

    def _model_meta(self):
        class Meta:
            app_label = self.app_label
            db_table = self.table_name
            verbose_name = self.name
        return Meta


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
    AbstractModelSchema base class. It is responsible for generating model
    fields with customized constraints.
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
        self._old_field = self.as_field()

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

    @property
    def schema_editor(self):
        return self.model.schema_editor

    @property
    def old_field(self):
        return self._old_field

    def as_field(self):
        """Return the Django model field instance with configured constraints."""
        options = {'null': not self.null, 'unique': self.unique}
        self._add_max_length_option(options)
        return self.field.as_field(**options)

    def _add_max_length_option(self, options):
        if self._requires_max_length():
            options['max_length'] = self.max_length or utils.default_max_length()
        return options

    def _requires_max_length(self):
        return self.field.constructor is models.CharField

    def save(self, **kwargs): # pylint: disable=arguments-differ
        self._check_null_is_valid()
        change_type = self._check_change_type()
        super().save(**kwargs)
        self._apply_schema_change(change_type)

    def _check_change_type(self):
        # TODO: change types enum, create, modify, none
        if self.id is None:
            return 'create'
        elif self._is_modified():
            return 'modify'
            
    def _apply_schema_change(self, change_type):
        self.model.save()
        if change_type == 'create':
            self.schema_editor.add_field(self)
        elif change_type == 'modify':
            self.schema_editor.alter_field(self)

    def _is_modified(self):
        return self.old_field != self.as_field()

    def _check_null_is_valid(self):
        if self.old_field.null and not self.null:
            raise exceptions.NullFieldChangedError(
                "{} cannot be changed to NOT NULL".format(self.column_name)
            )
