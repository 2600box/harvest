from rest_framework import serializers

from torrents.models import AlcazarClientConfig, Realm, Torrent, TorrentInfo, DownloadLocation
from trackers.registry import TrackerRegistry, PluginMissingException


class AlcazarClientConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlcazarClientConfig
        fields = ('base_url', 'token', 'unify_single_file_torrents')


class RealmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Realm
        fields = ('id', 'name')


class TorrentInfoSerializer(serializers.ModelSerializer):
    metadata = serializers.SerializerMethodField()

    def get_metadata(self, obj):
        try:
            tracker = TrackerRegistry.get_plugin(obj.realm.name)
        except PluginMissingException:
            return None
        serializer = tracker.torrent_info_metadata_serializer
        if not serializer:
            return None
        return serializer(obj).data

    class Meta:
        model = TorrentInfo
        fields = ('info_hash', 'tracker_id', 'fetched_datetime', 'metadata')


class TorrentSerializer(serializers.ModelSerializer):
    realm = serializers.PrimaryKeyRelatedField(queryset=Realm.objects.all())
    torrent_info = TorrentInfoSerializer()

    class Meta:
        model = Torrent
        fields = (
            'id', 'realm', 'torrent_info', 'info_hash', 'status', 'download_path', 'name', 'size', 'downloaded',
            'uploaded', 'download_rate', 'upload_rate', 'progress', 'added_datetime', 'error', 'tracker_error',
            'client',
        )


class DownloadLocationSerializer(serializers.ModelSerializer):
    realm = serializers.PrimaryKeyRelatedField(queryset=Realm.objects.all())

    class Meta:
        model = DownloadLocation
        fields = ('id', 'realm', 'pattern')
        depth = 1
