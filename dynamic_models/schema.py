"""Wrapper functions for performing runtime schema changes."""
from django.db import connections


class ModelSchemaEditor:
    def __init__(self, initial_model=None, db_name='default'):
        self.initial_model = initial_model
        self.db_name = db_name

    def update_table(self, new_model):
        if self.initial_model and self.initial_model != new_model:
            self.alter_table(new_model)
        elif not self.initial_model:
            self.create_table(new_model)
        self.initial_model = new_model

    def create_table(self, new_model):
        with connections[self.db_name].schema_editor() as editor:
            editor.create_model(new_model)

    def alter_table(self, new_model):
        old_name = self.initial_model._meta.db_table
        new_name = new_model._meta.db_table
        with connections[self.db_name].schema_editor() as editor:
            editor.alter_db_table(new_model, old_name, new_name)

    def drop_table(self, model):
        with connections[self.db_name].schema_editor() as editor:
            editor.delete_model(model)


class FieldSchemaEditor:
    def __init__(self, initial_field=None, db_name='default'):
        self.initial_field = initial_field
        self.db_name = db_name

    def update_column(self, model, new_field):
        if self.initial_field and self.initial_field != new_field:
            self.alter_column(model, new_field)
        elif not self.initial_field:
            self.add_column(model, new_field)
        self.initial_field = new_field

    def add_column(self, model, field):
        with connections[self.db_name].schema_editor() as editor:
            editor.add_field(model, field)

    def alter_column(self, model, new_field):
        with connections[self.db_name].schema_editor() as editor:
            editor.alter_field(model, self.initial_field, new_field)

    def drop_column(self, model, field):
        with connections[self.db_name].schema_editor() as editor:
            editor.remove_field(model, field)
