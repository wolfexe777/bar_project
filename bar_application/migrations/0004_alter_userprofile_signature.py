# Generated by Django 4.2.1 on 2023-06-03 15:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bar_application', '0003_remove_userprofile_digital_signature_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='signature',
            field=models.CharField(default=0, max_length=1000, verbose_name='Цифровая подпись'),
        ),
    ]
