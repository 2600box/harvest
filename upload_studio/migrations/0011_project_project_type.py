# Generated by Django 2.1.7 on 2019-04-08 19:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('upload_studio', '0010_auto_20190407_1935'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='project_type',
            field=models.CharField(default='', max_length=64),
            preserve_default=False,
        ),
    ]