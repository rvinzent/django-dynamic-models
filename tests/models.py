"""
Set up the test models inlcuding subclassed verisons of the Sbstract schema
models with additional common field types
"""
from django.db import models
from dynamic_models.models import AbstractModelSchema, AbstractFieldSchema


class SimpleModelSchema(AbstractModelSchema):
    extra_field = models.IntegerField()


class SimpleFieldSchema(AbstractFieldSchema):
    extra_field = models.IntegerField()