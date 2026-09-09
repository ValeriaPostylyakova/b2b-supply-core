from rest_framework import serializers

from apps.organizations.models import Organization


class OrganizationShortSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "type",
        ]

        read_only_fields = ["id", "type"]


class OrganizationBaseSerializer(OrganizationShortSerializer):
    inn = serializers.CharField(max_length=12)
    kpp = serializers.CharField(max_length=9)

    class Meta(OrganizationShortSerializer.Meta):
        fields = OrganizationShortSerializer.Meta.fields + [
            "inn",
            "kpp",
            "legal_address",
            "description",
            "verification_status",
            "created_at",
        ]

        read_only_fields = OrganizationShortSerializer.Meta.read_only_fields + [
            "verification_status",
            "created_at",
        ]
