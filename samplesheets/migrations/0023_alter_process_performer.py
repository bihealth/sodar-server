# Generated by Django 4.2.16 on 2024-10-30 13:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("samplesheets", "0022_update_igv_genome"),
    ]

    operations = [
        migrations.AlterField(
            model_name="process",
            name="performer",
            field=models.CharField(
                blank=True, help_text="Process performer (optional)", null=True
            ),
        ),
    ]
