# Generated by Django 2.1.7 on 2019-02-23 23:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('torrents', '0010_auto_20190223_0326'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='realm',
            options={'ordering': ('name',)},
        ),
    ]
