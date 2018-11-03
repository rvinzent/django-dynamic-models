"""
Provides wrapper functions for performing runtime schema changes with Django's
built in SchemaEditor class. 
"""

from django.db import connection


def create_table(model):
    """
    Creates a database table for the model.
    """
    with connection.schema_editor() as editor:
        editor.create_model(model)

def delete_table(model):
    """
    Deletes a database table for the model.
    """
    with connection.schema_editor() as editor:
        editor.delete_model(model)

def alter_table_name(model, old_name, new_name):
    """
    Changes the model's database table from old_name to new_name.
    """
    with connection.schema_editor() as editor:
        editor.alter_db_table(model, old_name, new_name)

def add_field(model, field):
    """
    Adds a field to the model's database table.
    """
    with connection.schema_editor() as editor:
        editor.add_field(model, field)

def remove_field(model, field):
    """
    Removes a field from the model's database table
    """
    with connection.schema_editor() as editor:
        editor.remove_field(model, field)

def alter_field(model, old_field, new_field):
    """
    Changes a model's database field from old_field to new_field including the
    colomn name and any null constraints.
    """
    with connection.schema_editor() as editor:
        editor.alter_field(model, old_field, new_field)
