"""Wrapper functions for performing runtime schema changes."""
from contextlib import contextmanager
from django.db import connection


class ModelSchemaEditor:
    def __init__(self, model_schema):
        self.editor = connection.schema_editor()
        self.schema = model_schema
        self.model = model_schema.as_model()

    def __enter__(self):
        return self.editor.__enter__()

    def __exit__(self, *args):
        return self.editor.__exit__(*args)       

    def create_table(self):
        """Create a database table for the model."""
        self.editor.create_model(self.model)

    def delete_table(self):
        """Delete a database table for the model."""
        self.editor.delete_model(self.model)

    def alter_table(self):
        """Change the model's database table from `old_name` to `new_name`."""
        old_name = self.schema.old_table_name
        new_name = self.schema.table_name
        if old_name != new_name:
            self.editor.alter_db_table(self.model, old_name, new_name)

    def add_field(self, field):
        """Add a field to the model's database table."""
        model_field = field.get_from_model(self.model)
        self.editor.add_field(self.model, model_field)

    def remove_field(self, field):
        """Remove a field from the model's database table."""
        model_field = field.field.get_from_model(self.model)
        self.editor.remove_field(self.model, model_field)

    def update_field(self, field):
        """Updates the field schema on the model's database table."""
        old_field = field.old_field
        new_field = field.field.get_from_model(self.model)
        self.editor.alter_field(self.model, old_field, new_field)
