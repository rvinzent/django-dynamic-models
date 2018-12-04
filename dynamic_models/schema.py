"""Wrapper functions for performing runtime schema changes."""
from django.db import connection


class ModelSchemaEditor:
    def __init__(self, model_schema):
        self.schema_editor = connection.schema_editor
        self.schema = model_schema

    def create_table(self):
        """Create a database table for the model."""
        with self.schema_editor() as editor:
            editor.create_model(self.schema.as_model())

    def delete_table(self):
        """Delete a database table for the model."""
        with self.schema_editor() as editor:
            editor.delete_model(self.schema.as_model())

    def alter_table(self):
        """Change the model's database table from `old_name` to `new_name`."""
        pass

    def _exectute_alter_table(self, model, changed):
        with self.schema_editor() as editor:
            editor.alter_db_table(model, changed.initial, changed.current)

    def add_field(self, field):
        """Add a field to the model's database table."""
        model = self.schema.as_model()
        model_field = model._meta.get_field(field.column_name)
        with self.schema_editor() as editor:
            editor.add_field(model, model_field)

    def remove_field(self, field):
        """Remove a field from the model's database table."""
        model = self.schema.as_model()
        model_field = model._meta.get_field(field.column_name)
        with self.schema_editor() as editor:
            editor.remove_field(model, model_field)

    def alter_field(self, field):
        """Updates the field schema on the model's database table."""
        pass
