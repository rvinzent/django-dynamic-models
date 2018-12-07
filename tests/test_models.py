from datetime import timedelta
from functools import partial
import pytest
from django.utils import timezone

from dynamic_models.models import DynamicModelField
from dynamic_models.utils import (
    db_table_exists, db_table_has_field, db_field_allows_null, is_registered
)
from .models import ModelSchema, FieldSchema

# pylint: disable=unused-argument,redefined-outer-name

@pytest.mark.django_db
class TestModelSchemaEditor:

    @pytest.fixture
    def no_existing_table(self, model_schema):
        if utils.db_table_exists(model_schema.db_table):
            model_schema.schema_editor.drop_table()

    def test_table_exists(self, model_schema):
        assert model_schema.schema_editor.exists(), "table not set up"
        model_schema.schema_editor.drop()
        assert not model_schema.schema_editor.exists()

    def test_create_table(self, model_schema):
        model_schema.schema_editor.drop_table()
        assert not db_table_exists(model_schema.db_table), "table not dropped"
        model_schema.schema_editor.create_table()
        assert db_table_exists(model_schema.db_table)

    def test_drop_table(self, model_schema):
        assert db_table_exists(model_schema.db_table), "table not set up"
        model_schema.schema_editor.drop_table()
        assert not db_table_exists(model_schema.db_table), "table not dropped"

    def test_alter_table(self, model_schema):
        intial_table_name = model_schema.db_table
        assert db_table_exists(intial_table_name), "table never existed"
        model_schema.name = 'different name'
        model_schema.schema_editor.alter_table()
        assert not db_table_exists(intial_table_name), "old table still exists"
        assert db_table_exists(model_schema.db_table), "new table does not exist"


@pytest.mark.django_db
class TestFieldSchemaEditor:

    @pytest.fixture
    def field_schema(self, model_schema, int_field_schema):
        return model_schema.add_field(int_field_schema)

    def test_column_exists(self, field_schema):
        assert field_schema.schema_editor.column_exists()
        field_schema.schema_editor.drop()
        assert not field_schema.schema_editor.column_exists()

    def test_create_field_schema(self, model_schema, field_schema):
        has_field = partial(db_table_has_field, model_schema.db_table)
        field_schema.schema_editor.drop()
        assert not has_field(field_schema.column_name), "field already present"
        field_schema.schema_editor.create()
        assert has_field(field_schema.column_name), "field not added"

    def test_drop_field_schema(self, model_schema, field_schema):
        has_field = partial(db_table_has_field, model_schema.db_table)
        assert has_field(field_schema.column_name), "field does not exist initially"
        field_schema.schema_editor.drop()
        assert not has_field(field_schema.column_name), "field not dropped"

    def test_alter_field_schema(self, model_schema, field_schema):
        has_field = partial(db_table_has_field, model_schema.db_table)
        initial_field_name = field_schema.column_name
        assert has_field(initial_field_name), "field not added correctly"

        field_schema.field.name = 'different name'
        field_schema.field.save()
        field_schema.schema_editor.alter()
        assert not has_field(initial_field_name), "old field still exists"
        assert has_field(field_schema.column_name), "new field does not exist"
