# Generated by Django 2.1.7 on 2019-03-31 02:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('upload_studio', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='project',
            name='current_step',
        ),
        migrations.AlterField(
            model_name='projectstep',
            name='executor_kwargs_json',
            field=models.TextField(default='{}'),
        ),
    ]
