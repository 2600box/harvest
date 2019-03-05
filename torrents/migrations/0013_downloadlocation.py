# Generated by Django 2.1.7 on 2019-03-02 19:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('torrents', '0012_auto_20190225_0147'),
    ]

    operations = [
        migrations.CreateModel(
            name='DownloadLocation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pattern', models.CharField(max_length=65536)),
                ('realm', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='download_locations', to='torrents.Realm')),
            ],
        ),
    ]