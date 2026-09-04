from rest_framework import serializers

from apps.orders.models import FileDocument
from config.storages import PrivateMediaStorage


class FileDocumentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = FileDocument
        fields = [
            "id",
            "document_type",
            "storage_key",
            "original_name",
            "content_type",
            "size",
            "download_url",
        ]

    def get_download_url(self, obj):
        storage = PrivateMediaStorage()

        from urllib.parse import quote

        filename = quote(obj.original_name or "document.pdf")
        content_disposition = f"attachment; filename*=UTF-8''{filename}"

        return storage.url(
            obj.storage_key,
            parameters={"ResponseContentDisposition": content_disposition},
        )
