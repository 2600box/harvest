# Generated by Django 2.1.7 on 2019-02-19 01:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('redacted', '0002_auto_20190219_0110'),
    ]

    operations = [
        migrations.AddField(
            model_name='redactedclientconfig',
            name='login_datetime',
            field=models.DateTimeField(null=True),
        ),
    ]
