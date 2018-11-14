from django.db.models import signals
from django.dispatch import receiver

from . import utils
from . import schema
from .exceptions import OutdatedModelError


def connect_schema_handlers(model):
    """
    Connect schema changing signal handlers to a concrete model.
    """
    signals.pre_delete.connect(delete_dynamic_model_table, sender=model)
    signals.post_save.connect(create_dynamic_model_table, sender=model)

def create_dynamic_model_table(sender, instance, created, **kwargs):
    model = instance.get_dynamic_model(regenerate=True)
    if created:
        schema.create_table(model)
    else:
        disconnect_dynamic_model(model)
    connect_dynamic_model(model)

def delete_dynamic_model_table(sender, instance, **kwargs):
    """
    Signal handler to delete dynamic models when the instance of their schema
    model is deleted.
    """
    model = instance.get_dynamic_model()
    schema.delete_table(model)

def connect_dynamic_model(model):
    """
    Connects a dynamically generated model to the check_latest_model handler.
    """
    signals.pre_save.connect(
        check_latest_model,
        sender=model,
        dispatch_uid=model.table_name
    )

def disconnect_dynamic_model(model):
    """
    Disconnects a dynamic model's pre_save handler.
    """
    return signals.pre_save.disconnect(check_latest_model, sender=model)

def check_latest_model(sender, instance, **kwargs):
    """
    Signal handler for dynamic models on pre_save to guard against the
    possibility of a model schema change between instance instantiation and
    record save.
    """
    # TODO: cache the last modified time instead of query on each save
    sender._schema.refresh_from_db()
    if not utils.has_current_schema(sender._schema, sender):
        raise OutdatedModelError(sender)

@receiver(signals.pre_save, sender='dynamic_models.DynamicModelField')
def track_old_model_field(sender, instance, created, **kwargs):
    """
    Keeps track of the old model field so schema changes can be applied post
    save if applicable. If the field is being saved for the first time, no
    action is required.
    """
    if created:
        return
    old_model = instance.model.get_dynamic_model()
    old_field = old_model._meta.get_field(instance.field.name)
    instance._old_model_field = old_field

@receiver(signals.post_save, sender='dynamic_models.DynamicModelField')
def apply_schema_changes(sender, instance, created, **kwargs):
    """
    If the instance is new, add it to the model's table. Otherwise, check if
    any of the schema have changed, and apply the schema changes if they have. 
    """
    model = instance.model.get_dynamic_model(regenerate=True)
    # Must get the field instance from the model for schema editor to work
    field = model._meta.get_field(instance.field.name)
    if created:
        schema.add_field(model, field)
    elif instance.tracker.changed():
        assert hasattr(instance, '_old_model_field'),\
            "old model field was not tracked"
        schema.alter_field(model, instance._old_model_field, field)
