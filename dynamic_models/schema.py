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


class ModelSchemaEditor:
    def __init__(self, model_schema):
        self.schema = model_schema
        self._editor = connection.schema_editor
        self._set_initial_state()

    def _set_initial_state(self):
        self._is_new_model = self.schema.id is None
        self._initial_table_name = self.schema.table_name
        self._set_intial_fields()

    def _set_intial_fields(self):
        if not self._is_new_model:
            self._initial_fields = self.schema.as_model()._meta.get_fields()
        else:
            self._initial_fields = {}

    def update_table(self):
        """Sync the table schema to the database."""
        if self._is_new_model:
            self._create_table()
        elif self.schema.table_name != self._initial_table_name:
            self._alter_table()
        self._set_initial_state()

    def delete_table(self):
        """Delete a database table for the model."""
        with self._editor() as editor:
            editor.delete_model(self.schema.as_model())

    def _create_table(self):
        with self._editor() as editor:
            editor.create_model(self.schema.as_model())

    def _alter_table(self):
        with self._editor() as editor:
            editor.alter_db_table(
                self.schema.as_model(),
                self._initial_table_name,
                self.schema.table_name
            )

    def update_field(self, field):
        """Update a field on the model with new constraints"""
        if field.column_name in self._initial_fields:
            self._alter_field(field)
        else:
            self._add_field(field)

    def delete_field(self, field):
        """Remove a field from the model's database table."""
        with self._editor() as editor:
            editor.remove_field(*self._model_with_field(field))
        self._set_initial_state()

    def _add_field(self, field):
        with self._editor() as editor:
            editor.add_field(*self._model_with_field(field))
        self._set_initial_state()

    def _alter_field(self, field):
        old_field = self._initial_fields[field.column_name]
        model, new_field = self._model_with_field(field)
        with self._editor() as editor:
            editor.alter_field(model, old_field, new_field)
        self._set_initial_state()

    def _model_with_field(self, field):
        model = self.schema.as_model()
        model_field = model._meta.get_field(field.column_name)
        return model, model_field

