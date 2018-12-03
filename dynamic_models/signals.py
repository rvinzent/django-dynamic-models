"""Signal handlers responsible for making schema changes for dynamic models.

`connect_model_schema_handlers` -- connects schema changers to model schema
`create_dynamic_model_table`    -- creates a new table for a dynamic model
`delete_dynamic_model_table`    -- deletes a table for a dynamic model
`connect_dynamic_model`         -- connect signal handlers to dynamic models
`disconnect_dynamic_model`      -- disconnect signal handlers from models
`check_latest_model`            -- ensure model is up-to-date
`track_old_model_field`         -- store pre_save field version
`apply_field_schema_changes`    -- change field schema if applicable
`remove_field_schema`           -- remove a field from a database table
"""
# pylint: disable=unused-argument

from django.db.models import signals
from django.dispatch import receiver

from . import schema
from .exceptions import OutdatedModelError


def connect_model_schema_handlers(model):
    """Connect schema changing signal handlers to a concrete model."""
    uid = _get_signal_uid(model._meta.model_name)
    signals.post_save.connect(
        create_dynamic_model_table,
        sender=model,
        dispatch_uid=uid
    )
    signals.pre_delete.connect(
        delete_dynamic_model_table,
        sender=model,
        dispatch_uid=uid
    )

def create_dynamic_model_table(sender, instance, created, **kwargs):
    """Create a database table when a dynamic model is saved."""
    model = instance.as_model()
    if created:
        schema.create_table(model)
    else:
        disconnect_dynamic_model(model._meta.model_name)
    connect_dynamic_model(model)

def delete_dynamic_model_table(sender, instance, **kwargs):
    """Delete dynamic models when the model schema is deleted."""
    model = instance.as_model()
    schema.delete_table(model)
    instance.unregister_model()

def connect_dynamic_model(model):
    """Connect a dynamically generated model to its signals.""" 
    signals.pre_save.connect(
        check_latest_model,
        sender=model,
        dispatch_uid=_get_signal_uid(model._meta.model_name)
    )

def disconnect_dynamic_model(model_name):
    """Disconnect a dynamicically generated model's signals."""
    uid = _get_signal_uid(model_name)
    return signals.pre_save.disconnect(check_latest_model, dispatch_uid=uid)

def check_latest_model(sender, instance, **kwargs):
    """Check that the schema being used is the most up-to-date.

    Called on pre_save to guard against the possibility of a model schema change
    between instance instantiation and record save.
    """
    # TODO: cache the last modified time instead to avoid query on each save
    sender._schema.refresh_from_db()
    if not sender._schema._has_current_schema(sender):
        raise OutdatedModelError("model {} has changed".format(sender.__name__))

# TODO: find better way to track old model field
@receiver(signals.pre_save, sender='dynamic_models.DynamicModelField')
def track_old_model_field(sender, instance, **kwargs):
    """Track of the old model field so schema changes can be applied correctly.

    If the field is being saved for the first time, no action is required.
    """
    if instance.id is None:
        return
    old_model = instance.model.as_model()
    old_field = old_model._meta.get_field(instance.field.column_name)
    instance._old_model_field = old_field

@receiver(signals.post_save, sender='dynamic_models.DynamicModelField')
def apply_field_schema_changes(sender, instance, created, **kwargs):
    """Apply necessary schema changes to database table."""
    model = instance.model.as_model()
    # Must get the field instance directly from the model
    field = model._meta.get_field(instance.field.column_name)
    if created:
        schema.add_field(model, field)
    elif instance.tracker.changed():
        assert hasattr(instance, '_old_model_field'),\
            "old model field was not tracked"
        schema.alter_field(model, instance._old_model_field, field)

@receiver(signals.pre_delete, sender='dynamic_models.DynamicModelField')
def remove_field_schema(sender, instance, **kwargs):
    """Remove the field from the database table when it is deleted."""
    model = instance.model.as_model()
    field = model._meta.get_field(instance.field.column_name)
    schema.remove_field(model, field)

def _get_signal_uid(model_name):
    return '{}_model_schema'.format(model_name)
