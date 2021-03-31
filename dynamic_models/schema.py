"""Wrapper functions for performing runtime schema changes."""
from functools import wraps

from django.db import connection
from django.db.utils import ProgrammingError


def set_constraints(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if connection.in_atomic_block:
            with connection.cursor() as cursor:
                cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
        return func(*args, **kwargs)
    return inner


class ModelSchemaEditor:
    def __init__(self, initial_model=None):
        self.initial_model = initial_model

    def update_table(self, new_model):
        if self.initial_model and self.initial_model != new_model:
            self.alter_table(new_model)
        elif not self.initial_model:
            self.create_table(new_model)
        self.initial_model = new_model

    @set_constraints
    def create_table(self, new_model):
        try:
            with connection.schema_editor() as editor:
                editor.create_model(new_model)
        except ProgrammingError:
            # TODO: I couldn't figure out why sometimes despite the
            # fact that the model exists, the initial_model is None and
            # therefore this method will be called which leads to this
            # error
            pass

    @set_constraints
    def alter_table(self, new_model):
        old_name = self.initial_model._meta.db_table
        new_name = new_model._meta.db_table
        with connection.schema_editor() as editor:
            editor.alter_db_table(new_model, old_name, new_name)

    @set_constraints
    def drop_table(self, model):
        with connection.schema_editor() as editor:
            editor.delete_model(model)


class FieldSchemaEditor:
    def __init__(self, initial_field=None):
        self.initial_field = initial_field

    def update_column(self, model, new_field):
        if self.initial_field and self.initial_field != new_field:
            self.alter_column(model, new_field)
        elif not self.initial_field:
            self.add_column(model, new_field)
        self.initial_field = new_field

    @set_constraints
    def add_column(self, model, field):
        with connection.schema_editor() as editor:
            editor.add_field(model, field)

    @set_constraints
    def alter_column(self, model, new_field):
        with connection.schema_editor() as editor:
            editor.alter_field(model, self.initial_field, new_field)

    @set_constraints
    def drop_column(self, model, field):
        with connection.schema_editor() as editor:
            editor.remove_field(model, field)
