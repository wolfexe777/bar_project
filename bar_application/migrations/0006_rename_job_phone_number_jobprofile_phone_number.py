# Generated by Django 4.2.1 on 2023-06-06 05:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bar_application', '0005_rename_phone_number_jobprofile_job_phone_number'),
    ]

    operations = [
        migrations.RenameField(
            model_name='jobprofile',
            old_name='job_phone_number',
            new_name='phone_number',
        ),
    ]
