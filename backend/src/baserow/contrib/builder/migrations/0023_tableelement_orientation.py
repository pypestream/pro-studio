# Generated by Django 4.1.13 on 2024-06-06 11:12

from django.db import migrations, models

from baserow.contrib.builder.elements.models import get_default_table_orientation


def populate_orientation_field(apps, schema_editor):
    """Add default orientation settings to all table elements."""

    TableElement = apps.get_model("builder", "tableelement")
    TableElement.objects.update(orientation={
        "smartphone": "horizontal",
        "tablet": "horizontal",
        "desktop": "horizontal",
    })


class Migration(migrations.Migration):
    dependencies = [
        ("builder", "0022_choiceelement_choiceelementoption_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="tableelement",
            name="orientation",
            field=models.JSONField(
                blank=True,
                default=get_default_table_orientation,
                help_text="The table orientation (horizontal or vertical) for each device type",
                null=True,
            ),
        ),
        migrations.RunPython(
            populate_orientation_field,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
