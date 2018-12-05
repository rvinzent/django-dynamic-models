"""Wrapper functions for performing runtime schema changes."""
from django.db import connection
from django.core.cache import cache
from . import utils


class ModelSchemaCacher:
    key_prefix = utils.cache_key_prefix()

    def get_last_modified(self, schema):
        return cache.get(self._make_cache_key(schema))

    def set_last_modified(self, schema, timeout=60*60*24*3):
        return cache.set(self._make_cache_key(schema), schema.modified, timeout)

    def delete(self, schema):
        return cache.delete(self._make_cache_key(schema))

    @classmethod
    def _make_cache_key(cls, schema):
        return '_'.join([cls.key_prefix, schema.model_name])


class BaseSchemaEditor:
    def __init__(self, schema):
        self.schema = schema
        self.editor = connection.schema_editor
        self.initial_name = self.get_name()

    def get_model(self):
        return self.schema.as_model()

    def get_name(self):
        raise NotImplementedError()

    def exists(self):
        raise NotImplementedError()

    def update(self):
        """Either update or create the database schema."""
        if not self.exists():
            self.create()
        elif self.is_changed():
            self.alter()
            self.sync()

    def create(self):
        raise NotImplementedError()

    def alter(self):
        raise NotImplementedError()

    def drop(self):
        raise NotImplementedError()

    def sync(self):
        self.initial_name = self.get_name()

    def is_changed(self):
        return self.initial_name != self.get_name()


class ModelSchemaEditor(BaseSchemaEditor):
    def get_name(self):
        """Return the name of the table."""
        return self.schema.table_name

    def exists(self):
        """Check if the table exists in the database."""
        return utils.db_table_exists(self.initial_name)

    def create(self):
        """Create a database table for this model."""
        with self.editor() as e:
            e.create_model(self.get_model())

    def alter(self):
        """Change the model's table_name to the currently set name."""
        with self.editor() as e:
            e.alter_db_table(self.get_model(), self.initial_name, self.get_name())

    def drop(self):
        """Delete a database table for the model."""
        with self.editor() as e:
            e.delete_model(self.get_model())


class FieldSchemaEditor(BaseSchemaEditor):
    def __init__(self, model_schema, field_schema):
        super().__init__(self, model_schema)
        self.field_schema = field_schema
        self.initial_field = self.get_model()._meta.get_field(self.initial_name)

    def get_name(self):
        """Return the column name of the field."""
        return self.field_schema.column_name

    def get_field(self, model=None):
        """Return the field from the model."""
        if model is None:
            model = self.get_model()
        return model._meta.get_field(self.get_name())

    def get_model_with_field(self):
        """Return both the model and the field."""
        model = self.get_model()
        field = self.get_field(model)
        return model, field

    def exists(self):
        """Check if the column exists on the model's database table."""
        return utils.db_table_has_field(
            self.schema.table_name,
            self.initial_name
        )

    def create(self):
        """Add a field to this model's database table."""
        model = self.get_model()
        with self.editor() as e:
            e.add_field(model, self.initial_field)

    def drop(self):
        """Remove a field from the model's database table."""
        model, field = self.get_model_with_field()
        with self.editor() as e:
            e.remove_field(model, field)

    def alter(self):
        """Alter field schema including constraints on the model's table."""
        model, new_field = self.get_model_with_field()
        with self.editor() as e:
            e.alter_field(model, self.initial_field, new_field)

    def is_changed(self):
        """Check if the field schema has changed."""
        return self.initial_field == self.get_field()

    def sync(self):
        super().sync()
        self.initial_field = self.get_field()
