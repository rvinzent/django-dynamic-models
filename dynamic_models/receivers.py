from django.dispatch import receiver
from django.db.models.signals import pre_delete

from . import utils

ModelFieldSchema = utils.get_model_field_schema_model() 


@receiver(pre_delete, sender=ModelFieldSchema)
def drop_table_column(sender, instance, **kwargs):  # pylint: disable=unused-argument
    instance.drop_column()
    instance.update_last_modified()


@receiver(pre_delete, sender=ModelFieldSchema.ModelSchema)
def drop_relation_by_model(sender, instance, **kwargs):  # pylint: disable=unused-argument
    instance.destroy_model()
    ModelFieldSchema.objects.filter(model_id=instance.pk).delete()


@receiver(pre_delete, sender=ModelFieldSchema.FieldSchema)
def drop_relation_by_field(sender, instance, **kwargs):  # pylint: disable=unused-argument
    ModelFieldSchema.objects.filter(field_id=instance.pk).delete()
