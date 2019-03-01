# Generated by Django 2.1.7 on 2019-02-23 00:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('torrents', '0006_auto_20190222_2325'),
    ]

    operations = [
        migrations.RenameField(
            model_name='torrent',
            old_name='download_location',
            new_name='download_path',
        ),
        migrations.AlterField(
            model_name='torrentfile',
            name='torrent_info',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='torrent_file', to='torrents.TorrentInfo'),
        ),
    ]
