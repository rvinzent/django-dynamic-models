"""
Set up the test models inlcuding subclassed verisons of the Sbstract schema
models with additional common field types
"""
from dynamic_models.models import AbstractModelSchema, AbstractFieldSchema


class ModelSchema(AbstractModelSchema):
    pass


class FieldSchema(AbstractFieldSchema):
    pass