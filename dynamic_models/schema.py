"""Wrapper functions for performing runtime schema changes."""
from django.db import connection
from django.core.cache import cache
from django.core.exceptions import FieldDoesNotExist
from . import utils


class ModelSchemaChecker:
    key_prefix = utils.cache_key_prefix()

    def __init__(self, schema):
        self.schema = schema
        self.cache_key = self._make_cache_key(schema)

    def get_last(self):
        return cache.get(self.cache_key)

    def update(self, time, timeout=60*60*24*2):
        return cache.set(self.cache_key, time, timeout)

    def is_current_model(self, model):
        last_modified = self.get_last()
        return last_modified and last_modified <= model._declared

    def delete(self):
        return cache.delete(self.cache_key)

    @classmethod
    def _make_cache_key(cls, schema):
        return '_'.join([cls.key_prefix, schema.model_name])


class BaseSchemaEditor:
    def __init__(self, schema):
        self.schema = schema
        self.editor = connection.schema_editor
        self.set_initial()

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
            self.set_initial()

    def create(self):
        raise NotImplementedError()

    def alter(self):
        raise NotImplementedError()

    def drop(self):
        raise NotImplementedError()

    def set_initial(self):
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
        self.field_schema = field_schema
        super().__init__(model_schema)

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

    def set_initial(self):
        super().set_initial()
        self.initial_field = self.get_field()
