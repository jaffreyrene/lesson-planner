# Generated by Django 5.2 on 2025-04-23 20:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lesson_plans', '0004_userprofile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='role',
            field=models.CharField(choices=[('admin', 'Admin'), ('client', 'Client')], max_length=20),
        ),
    ]
