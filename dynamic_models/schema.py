"""Wrapper functions for performing runtime schema changes."""
from django.db import connection


class ModelSchemaEditor:
    def __init__(self, initial_model=None):
        self.initial_model = initial_model
        self.editor = connection.schema_editor

    def update_table(self, new_model):
        if self.initial_model and self.is_changed(new_model):
            self.alter_table(new_model)
        elif not self.initial_model:
            self.create_table(new_model)
        self.initial_model = new_model

    def is_changed(self, model):
        return self.initial_model != model

    def create_table(self, new_model):
        """Create a database table for this model."""
        with self.editor() as editor:
            editor.create_model(new_model)

    def alter_table(self, new_model):
        """Change the model's db_table to the currently set name."""
        old_name = self.initial_model._meta.db_table
        new_name = new_model._meta.db_table
        with self.editor() as editor:
            editor.alter_db_table(new_model, old_name, new_name)

    def drop_table(self, model):
        """Delete a database table for the model."""
        with self.editor() as editor:
            editor.delete_model(model)


class FieldSchemaEditor:
    def __init__(self, initial_field=None):
        self.initial_field = initial_field
        self.editor = connection.schema_editor

    def update_column(self, model, new_field):
        if self.initial_field and self.is_changed(new_field):
            self.alter_column(model, new_field)
        elif not self.initial_field:
            self.add_column(model, new_field)

    def is_changed(self, field):
        """Check if the field schema has changed."""
        return self.initial_field != field

    def add_column(self, model, field):
        """Add a field to this model's database table."""
        with self.editor() as editor:
            editor.add_field(model, field)

    def alter_column(self, model, new_field):
        """Alter field schema including constraints on the model's table."""
        with self.editor() as editor:
            editor.alter_field(model, self.initial_field, new_field)

    def drop_column(self, model, field):
        """Remove a field from the model's database table."""
        with self.editor() as editor:
            editor.remove_field(model, field)
