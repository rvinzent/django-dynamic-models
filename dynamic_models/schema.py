"""Wrapper functions for performing runtime schema changes."""
from django.db import connection
from django.core.exceptions import FieldDoesNotExist
from . import utils


class ModelSchemaEditor:
    def __init__(self, schema):
        self.schema = schema
        self.editor = connection.schema_editor
        self.initial_name = schema.db_table

    def update_table(self):
        if not self.table_exists():
            self.create_table()
        elif self.is_changed():
            self.alter_table()

    def table_exists(self):
        """Check if the table exists in the database."""
        return utils.db_table_exists(self.initial_name)

    def is_changed(self):
        return self.initial_name != self.schema.db_table

    def create_table(self):
        """Create a database table for this model."""
        with self.editor() as e:
            e.create_model(self.schema.as_model())

    def alter_table(self):
        """Change the model's db_table to the currently set name."""
        with self.editor() as e:
            e.alter_db_table(self.schema.as_model(), self.initial_name, self.schema.db_table)

    def drop_table(self):
        """Delete a database table for the model."""
        with self.editor() as e:
            e.delete_model(self.schema.as_model())


class FieldSchemaEditor:
    def __init__(self, model_field_schema):
        self.schema = model_field_schema
        self.initial_field = field_schema.field

    def update_column(self):
        if not self.column_exists():
            self.add_column()
        elif self.is_changed():
            self.alter_column()

    def column_exists(self):
        """Check if the column exists on the model's database table."""
        return utils.db_table_has_field(
            self.model_schema.db_table,
            self.initial_field.column
        )

    def is_changed(self):
        """Check if the field schema has changed."""
        return self.initial_field == self.schema.field

    def add_column(self):
        """Add a field to this model's database table."""
        with self.editor() as e:
            e.add_field(self.schema.model, self.initial_field)

    def alter_column(self):
        """Alter field schema including constraints on the model's table."""
        with self.editor() as e:
            e.alter_field(self.schema.model, self.initial_field, self.schema.field)

    def drop_column(self):
        """Remove a field from the model's database table."""
        with self.editor() as e:
            e.remove_field(self.schema.model, self.schema.field)
