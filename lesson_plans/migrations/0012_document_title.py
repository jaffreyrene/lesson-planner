# Generated by Django 5.2 on 2025-05-30 16:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lesson_plans', '0011_outputformat'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='title',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
