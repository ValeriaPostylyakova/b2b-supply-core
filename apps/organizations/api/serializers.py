from rest_framework import serializers

from apps.organizations.models import Organization


class OrganizationShortSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)

    class Meta:
        model = Organization
        fields = ["id", "name"]


class OrganizationBaseSerializer(OrganizationShortSerializer):
    class Meta(OrganizationShortSerializer.Meta):
        fields = OrganizationShortSerializer.Meta.fields + ["type"]
