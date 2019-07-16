"""
Set up the test models inlcuding subclassed verisons of the Sbstract schema
models with additional common field types
"""
from dynamic_models.models import AbstractModelSchema, AbstractFieldSchema, AbstractModelFieldSchema


class ModelSchema(AbstractModelSchema):
    pass


class FieldSchema(AbstractFieldSchema):
    pass


class ModelFieldSchema(AbstractModelFieldSchema):
    ModelSchema = ModelSchema
    FieldSchema = FieldSchema

    class Meta(AbstractModelFieldSchema.Meta):
        pass
