import pytest
from django.db import models
from dynamic_models.utils import db_table_exists, db_table_has_field
from dynamic_models.schema import ModelSchemaEditor, FieldSchemaEditor


@pytest.fixture(scope="module")
def generate_model():
    def _generate_model(name, **fields):
        fields["__module__"] = "tests.models"
        return type(name, (models.Model,), fields)

    return _generate_model


@pytest.fixture
def initial_model(generate_model):
    return generate_model("InitialModel", integer=models.IntegerField())


@pytest.mark.django_db
class TestModelSchemaEditor:
    @pytest.fixture
    def changed_model(self, generate_model):
        return generate_model("ChangedModel", integer=models.IntegerField())

    @pytest.fixture
    def initial_table(self, initial_model):
        ModelSchemaEditor().create_table(initial_model)

    def test_create_table(self, initial_model):
        assert not db_table_exists("tests_initialmodel")
        ModelSchemaEditor().create_table(initial_model)
        assert db_table_exists("tests_initialmodel")

    def test_update_table_creates_if_not_exists(self, initial_model):
        assert not db_table_exists("tests_initialmodel")
        ModelSchemaEditor().update_table(initial_model)
        assert db_table_exists("tests_initialmodel")

    @pytest.mark.usefixtures("initial_table")
    def test_update_table_alters_if_table_exists(self, initial_model, changed_model):
        assert db_table_exists("tests_initialmodel")
        assert not db_table_exists("tests_changedmodel")
        ModelSchemaEditor(initial_model).update_table(changed_model)
        assert db_table_exists("tests_changedmodel")
        assert not db_table_exists("tests_initialmodel")

    @pytest.mark.usefixtures("initial_table")
    def test_alter_table(self, initial_model, changed_model):
        assert db_table_exists("tests_initialmodel")
        assert not db_table_exists("tests_changedmodel")
        ModelSchemaEditor(initial_model).alter_table(changed_model)
        assert db_table_exists("tests_changedmodel")
        assert not db_table_exists("tests_initialmodel")

    @pytest.mark.usefixtures("initial_table")
    def test_drop_table(self, initial_model):
        assert db_table_exists("tests_initialmodel")
        ModelSchemaEditor().drop_table(initial_model)
        assert not db_table_exists("tests_initialmodel")


@pytest.mark.django_db
class TestFieldSchemaEditor:
    @pytest.fixture
    def bare_model(self, generate_model):
        return generate_model("InitialModel")

    @pytest.fixture
    def bare_table(self, bare_model):
        ModelSchemaEditor().create_table(bare_model)

    @pytest.fixture
    def initial_field_table(self, initial_model):
        ModelSchemaEditor().create_table(initial_model)

    @pytest.fixture
    def changed_field_constraint_model(self, generate_model):
        return generate_model("InitialModel", integer=models.IntegerField(null=True))

    @pytest.fixture
    def changed_field_name_model(self, generate_model):
        return generate_model("InitialModel", changed=models.IntegerField())

    @pytest.mark.usefixtures("bare_table")
    def test_add_column(self, initial_model):
        assert not db_table_has_field("tests_initialmodel", "integer")
        new_field = initial_model._meta.get_field("integer")
        FieldSchemaEditor().add_column(initial_model, new_field)
        assert db_table_has_field("tests_initialmodel", "integer")

    @pytest.mark.usefixtures("bare_table")
    def test_update_column_creates_if_not_exists(self, initial_model):
        initial_field = initial_model._meta.get_field("integer")
        assert not db_table_has_field("tests_initialmodel", "integer")
        FieldSchemaEditor().update_column(initial_model, initial_field)
        assert db_table_has_field("tests_initialmodel", "integer")

    @pytest.mark.usefixtures("initial_field_table")
    def test_update_column_alters_if_exists(
        self, initial_model, changed_field_name_model
    ):
        initial_field = initial_model._meta.get_field("integer")
        new_field = changed_field_name_model._meta.get_field("changed")
        assert db_table_has_field("tests_initialmodel", "integer")
        assert not db_table_has_field("tests_initialmodel", "changed")

        FieldSchemaEditor(initial_field).update_column(
            changed_field_name_model, new_field
        )

        assert db_table_has_field("tests_initialmodel", "changed")
        assert not db_table_has_field("tests_initialmodel", "integer")

    @pytest.mark.usefixtures("initial_field_table")
    def test_alter_column(self, initial_model, changed_field_name_model):
        initial_field = initial_model._meta.get_field("integer")
        new_field = changed_field_name_model._meta.get_field("changed")
        assert db_table_has_field("tests_initialmodel", "integer")
        assert not db_table_has_field("tests_initialmodel", "changed")

        FieldSchemaEditor(initial_field).alter_column(
            changed_field_name_model, new_field
        )

        assert db_table_has_field("tests_initialmodel", "changed")
        assert not db_table_has_field("tests_initialmodel", "integer")

    @pytest.mark.usefixtures("initial_field_table")
    def test_drop_column(self, initial_model):
        field = initial_model._meta.get_field("integer")
        assert db_table_has_field("tests_initialmodel", "integer")
        FieldSchemaEditor().drop_column(initial_model, field)
        assert not db_table_has_field("tests_initialmodel", "integer")
