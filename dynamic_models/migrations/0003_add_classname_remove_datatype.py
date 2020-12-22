from django.db import migrations, models
from dynamic_models.models import FieldKwargsJSON


def set_defaults(apps, schema_editor):
    DATA_TYPES = {
        "character": "django.db.models.CharField",
        "text": "django.db.models.TextField",
        "integer": "django.db.models.IntegerField",
        "float": "django.db.models.FloatField",
        "boolean": "django.db.models.BooleanField",
        "date": "django.db.models.DateTimeField",
    }
    fieldschemas = apps.get_model("dynamic_models", "fieldschema")
    for fieldschema in fieldschemas.objects.all().iterator():
        fieldschema.class_name = DATA_TYPES[fieldschema.data_type]
        kwargs = {"unique": fieldschema.unique, "null": fieldschema.null}
        if fieldschema.data_type == "character":
            kwargs["max_length"] = fieldschema.max_length
        fieldschema.kwargs = kwargs
        fieldschema.save()


class Migration(migrations.Migration):

    dependencies = [
        ("dynamic_models", "0002_remove_modelschema__modified"),
    ]

    operations = [
        migrations.AddField(
            model_name="fieldschema",
            name="class_name",
            field=models.TextField(null=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="fieldschema",
            name="kwargs",
            field=FieldKwargsJSON(null=True),
        ),
        migrations.RunPython(set_defaults),
        migrations.AlterField(
            model_name="fieldschema",
            name="class_name",
            field=models.TextField(null=False),
        ),
        migrations.AlterField(
            model_name="fieldschema",
            name="kwargs",
            field=FieldKwargsJSON(default=dict, null=False),
        ),
        migrations.RemoveField(
            model_name="fieldschema",
            name="null",
        ),
        migrations.RemoveField(
            model_name="fieldschema",
            name="data_type",
        ),
        migrations.RemoveField(
            model_name="fieldschema",
            name="max_length",
        ),
        migrations.RemoveField(
            model_name="fieldschema",
            name="unique",
        ),
    ]
