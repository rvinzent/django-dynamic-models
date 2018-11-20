from django.db import models
from dynamic_models.models import AbstractModelSchema, AbstractFieldSchema


class RelatedModel(models.Model):
    name = models.CharField(max_length=32)


class SimpleModelSchema(AbstractModelSchema):
    normal_field = models.IntegerField()
    related_field = models.ForeignKey(RelatedModel, on_delete=models.CASCADE)


class SimpleFieldSchema(AbstractFieldSchema):
    normal_field = models.IntegerField()
    related_field = models.ForeignKey(RelatedModel, on_delete=models.CASCADE)